"""Turn uploaded files into plain-text sections."""
import csv
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

from pypdf import PdfReader

CSV_ROWS_PER_SECTION = 25


class ParseError(Exception):
    """Raised when a file cannot be read."""


@dataclass
class ParsedSection:
    text: str
    page_number: Optional[int] = None


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding).replace("\r\n", "\n")
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace").replace("\r\n", "\n")


def parse_pdf(path: Path) -> Iterator[ParsedSection]:
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ParseError("PDF is password protected")
        for number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                yield ParsedSection(text=text, page_number=number)
    except ParseError:
        raise
    except Exception as exc:
        raise ParseError(f"Could not read PDF: {exc}") from exc


def parse_txt(path: Path) -> Iterator[ParsedSection]:
    text = _read_text(path).strip()
    if text:
        yield ParsedSection(text=text)


def _column_name(header: list, index: int) -> str:
    if index < len(header) and header[index].strip():
        return header[index].strip()
    return "column_" + str(index + 1)


def parse_csv(path: Path) -> Iterator[ParsedSection]:
    text = _read_text(path)
    if not text.strip():
        return
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text, newline=""), dialect)
    header = next(reader, None)
    if not header:
        return

    lines = []
    for row_number, row in enumerate(reader, start=1):
        pairs = [
            _column_name(header, i) + ": " + value.strip()
            for i, value in enumerate(row)
            if value.strip()
        ]
        if not pairs:
            continue
        lines.append("Row " + str(row_number) + ": " + " | ".join(pairs))
        if len(lines) == CSV_ROWS_PER_SECTION:
            yield ParsedSection(text="\n".join(lines))
            lines = []
    if lines:
        yield ParsedSection(text="\n".join(lines))


def parse_file(path: Path, file_type: str) -> Iterator[ParsedSection]:
    parsers = {"PDF": parse_pdf, "TXT": parse_txt, "CSV": parse_csv}
    parser = parsers.get(file_type.upper())
    if parser is None:
        raise ParseError("Unsupported file type: " + file_type)
    return parser(path)