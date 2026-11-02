"""Measure retrieval quality: Recall@5 and MRR@10 for vector, keyword and hybrid search.

Run from the ai-service folder:
    python -m app.evaluation.run_eval --source-id <uuid of the ingested source>
"""
import argparse
import csv
import json
import re
import statistics
import time
from collections import defaultdict
from pathlib import Path
from uuid import UUID

from app.retrieval.search import MODES, retrieve

TOP_K = 10
RECALL_K = 5
REPO_ROOT = Path(__file__).resolve().parents[3]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


def _matches(hit, entry) -> bool:
    """A chunk is relevant if it is on the expected page and contains the evidence phrase."""
    return hit.page_number == entry["page"] and _norm(entry["evidence"]) in _norm(hit.content)


def load_questions(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def percentile(values, pct):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, int(round(pct / 100 * (len(ordered) - 1))))
    return ordered[index]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--questions", default=str(REPO_ROOT / "evaluation" / "questions.jsonl"))
    parser.add_argument("--out", default=str(REPO_ROOT / "evaluation" / "results" / "retrieval_eval.csv"))
    args = parser.parse_args()

    source_id = UUID(args.source_id)
    questions = load_questions(Path(args.questions))
    answerable = [q for q in questions if q["answerable"]]
    print(f"Questions: {len(questions)} ({len(answerable)} answerable, "
          f"{len(questions) - len(answerable)} unanswerable)")

    retrieve("warm up", [source_id], "vector", 1)  # load the model before timing

    rows = []
    stats = {m: {"recall": [], "hit": [], "rr": [], "lat": [], "by_type": defaultdict(list)} for m in MODES}
    top1 = {"answerable": [], "unanswerable": []}

    for q in questions:
        for mode in MODES:
            started = time.perf_counter()
            hits = retrieve(q["question"], [source_id], mode, TOP_K)
            latency_ms = (time.perf_counter() - started) * 1000
            top1_score = hits[0].score if hits else 0.0
            top1_page = hits[0].page_number if hits else None

            recall = hit_flag = rr = first_rank = None
            if q["answerable"]:
                entries = q["expected"]
                top_k_hits = hits[:RECALL_K]
                found = [any(_matches(h, e) for h in top_k_hits) for e in entries]
                recall = sum(found) / len(entries)
                hit_flag = 1.0 if any(found) else 0.0
                ranks = [i for i, h in enumerate(hits, 1) if any(_matches(h, e) for e in entries)]
                first_rank = min(ranks) if ranks else None
                rr = 1.0 / first_rank if first_rank else 0.0
                s = stats[mode]
                s["recall"].append(recall)
                s["hit"].append(hit_flag)
                s["rr"].append(rr)
                s["by_type"][q["type"]].append(recall)
                if mode == "vector":
                    top1["answerable"].append(top1_score)
            elif mode == "vector":
                top1["unanswerable"].append(top1_score)
            stats[mode]["lat"].append(latency_ms)
            rows.append({"id": q["id"], "type": q["type"], "mode": mode, "answerable": q["answerable"],
                         "recall_at_5": recall, "hit_at_5": hit_flag, "first_relevant_rank": first_rank,
                         "reciprocal_rank": rr, "latency_ms": round(latency_ms, 1),
                         "top1_page": top1_page, "top1_score": round(top1_score, 4)})

    print(f"\nOverall (N = {len(answerable)} answerable questions)")
    print(f"{'mode':<10}{'Recall@5':>10}{'Hit@5':>8}{'MRR@10':>9}{'median ms':>11}{'p95 ms':>9}")
    for mode in MODES:
        s = stats[mode]
        print(f"{mode:<10}{statistics.mean(s['recall']):>10.3f}{statistics.mean(s['hit']):>8.3f}"
              f"{statistics.mean(s['rr']):>9.3f}{statistics.median(s['lat']):>11.1f}{percentile(s['lat'], 95):>9.1f}")

    types = sorted({t for m in MODES for t in stats[m]["by_type"]})
    print("\nRecall@5 by question type (number of questions in brackets)")
    print(f"{'type':<14}" + "".join(f"{m:>10}" for m in MODES))
    for t in types:
        n = len(stats["vector"]["by_type"][t])
        print(f"{t + ' (' + str(n) + ')':<14}" + "".join(
            f"{statistics.mean(stats[m]['by_type'][t]):>10.3f}" for m in MODES))

    a, u = top1["answerable"], top1["unanswerable"]
    print("\nTop-1 vector similarity (for choosing the abstention threshold)")
    print(f"  answerable   : min {min(a):.3f} | mean {statistics.mean(a):.3f}")
    print(f"  unanswerable : mean {statistics.mean(u):.3f} | max {max(u):.3f}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nPer-question results saved to {out}")


if __name__ == "__main__":
    main()