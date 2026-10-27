import sys
from pathlib import Path

from app.ingestion.chunker import CHUNK_SIZE, chunk_sections
from app.ingestion.parsers import ParsedSection, parse_file


def report(name, sections):
    chunks = chunk_sections(sections)
    print(f"\n=== {name} ===")
    print(f"sections: {len(sections)} | chunks: {len(chunks)}")
    if not chunks:
        return
    lengths = [len(c.text) for c in chunks]
    print(f"length min / avg / max: {min(lengths)} / {sum(lengths) // len(lengths)} / {max(lengths)} (limit {CHUNK_SIZE})")
    pairs = [(a, b) for a, b in zip(chunks, chunks[1:])
             if a.page_number is not None and a.page_number == b.page_number]
    if pairs:
        ok = all(a.text[-40:] in b.text for a, b in pairs)
        print("overlap between neighbouring chunks on the same page:", "OK" if ok else "CHECK")
    else:
        print("overlap check: not applicable (no neighbouring chunks on one page)")
    for c in chunks[:3]:
        label = f"page {c.page_number}" if c.page_number else "no page"
        print(f"  #{c.index} [{label}] {len(c.text)} chars: {c.text[:80]!r}")


if len(sys.argv) > 1:
    for arg in sys.argv[1:]:
        p = Path(arg)
        report(p.name, list(parse_file(p, p.suffix.lstrip(".").upper())))
else:
    long_text = " ".join(
        f"Vendor spending in region {i} rose because of contract number {i}." for i in range(1, 120)
    )
    report("sample text (2 pages)", [ParsedSection(long_text, 1), ParsedSection(long_text[:2500], 2)])