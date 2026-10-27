import sys
import tempfile
from pathlib import Path

from app.ingestion.parsers import parse_file


def show(path: Path):
    file_type = path.suffix.lstrip(".").upper()
    sections = list(parse_file(path, file_type))
    print(f"\n=== {path.name} ({file_type}): {len(sections)} section(s) ===")
    for s in sections[:3]:
        label = f"page {s.page_number}" if s.page_number else "no page"
        preview = s.text[:200].replace("\n", " / ")
        print(f"[{label}] {preview}")


if len(sys.argv) > 1:
    for arg in sys.argv[1:]:
        show(Path(arg))
else:
    tmp = Path(tempfile.mkdtemp())
    csv_file = tmp / "sample.csv"
    csv_file.write_text("vendor,amount,quarter\nacme,1000,Q3\nbeta,2500,Q3\n", encoding="utf-8")
    txt_file = tmp / "sample.txt"
    txt_file.write_text("Vendor spending increased in Q3 because of new contracts.", encoding="utf-8")
    show(csv_file)
    show(txt_file)