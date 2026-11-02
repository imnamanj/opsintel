"""Retrieval: vector search, keyword search and Reciprocal Rank Fusion."""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence
from uuid import UUID

from app.db import connect
from app.ingestion.embedder import embed_texts

RRF_K = 60
CANDIDATES = 20
MODES = ("vector", "keyword", "hybrid")


@dataclass
class Hit:
    chunk_id: str
    source_id: str
    chunk_index: int
    page_number: Optional[int]
    content: str
    score: float
    method: str


def _vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(str(float(x)) for x in vector) + "]"


def _to_hits(rows, method: str) -> List[Hit]:
    return [
        Hit(chunk_id=str(r[0]), source_id=str(r[1]), chunk_index=r[2],
            page_number=r[3], content=r[4], score=float(r[5]), method=method)
        for r in rows
    ]


def vector_search(query_vector: Sequence[float], source_ids: Sequence[UUID],
                  limit: int = CANDIDATES) -> List[Hit]:
    """Nearest chunks by cosine distance, only from READY sources the caller may read."""
    literal = _vector_literal(query_vector)
    sql = (
        "select c.id, d.source_id, c.chunk_index, c.page_number, c.content, "
        "1 - (c.embedding <=> %s::vector) as score "
        "from document_chunks c "
        "join documents d on d.id = c.document_id "
        "join data_sources s on s.id = d.source_id "
        "where d.source_id = any(%s) and s.status = 'READY' "
        "order by c.embedding <=> %s::vector, c.id "
        "limit %s"
    )
    with connect() as conn:
        rows = conn.execute(sql, (literal, list(source_ids), literal, limit)).fetchall()
    return _to_hits(rows, "vector")


def _keyword_query(question: str) -> str:
    """Turn a question into an OR query of plain words (safe for to_tsquery)."""
    seen, words = set(), []
    for word in re.findall(r"[a-z0-9]+", question.lower()):
        if word not in seen:
            seen.add(word)
            words.append(word)
    return " | ".join(words)


def keyword_search(question: str, source_ids: Sequence[UUID],
                   limit: int = CANDIDATES) -> List[Hit]:
    """Full-text search with ts_rank, only from READY sources the caller may read."""
    query = _keyword_query(question)
    if not query:
        return []
    sql = (
        "select c.id, d.source_id, c.chunk_index, c.page_number, c.content, "
        "ts_rank(c.tsv, q.query) as score "
        "from document_chunks c "
        "join documents d on d.id = c.document_id "
        "join data_sources s on s.id = d.source_id, "
        "to_tsquery('english', %s) as q(query) "
        "where d.source_id = any(%s) and s.status = 'READY' and c.tsv @@ q.query "
        "order by score desc, c.id "
        "limit %s"
    )
    with connect() as conn:
        rows = conn.execute(sql, (query, list(source_ids), limit)).fetchall()
    return _to_hits(rows, "keyword")


def reciprocal_rank_fusion(*ranked_lists: Sequence[Hit], k: int = RRF_K) -> List[Hit]:
    """Merge rankings: each list adds 1 / (k + rank) to a chunk's score."""
    scores: Dict[str, float] = {}
    first_seen: Dict[str, Hit] = {}
    for hits in ranked_lists:
        for rank, hit in enumerate(hits, start=1):
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
            first_seen.setdefault(hit.chunk_id, hit)
    fused = []
    for chunk_id in sorted(scores, key=lambda cid: (-scores[cid], cid)):
        h = first_seen[chunk_id]
        fused.append(Hit(h.chunk_id, h.source_id, h.chunk_index, h.page_number,
                         h.content, scores[chunk_id], "hybrid"))
    return fused


def retrieve(question: str, source_ids: Sequence[UUID], mode: str = "hybrid",
             top_k: int = 5) -> List[Hit]:
    if mode not in MODES:
        raise ValueError("mode must be one of " + ", ".join(MODES))
    if not source_ids:
        return []
    if mode == "keyword":
        return keyword_search(question, source_ids)[:top_k]
    query_vector = embed_texts([question])[0]
    if mode == "vector":
        return vector_search(query_vector, source_ids)[:top_k]
    return reciprocal_rank_fusion(
        vector_search(query_vector, source_ids),
        keyword_search(question, source_ids),
    )[:top_k]