"""Split parsed sections into overlapping chunks ready for embedding."""
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

from app.ingestion.parsers import ParsedSection

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
_SEPARATORS = ("\n\n", "\n", ". ", " ")


@dataclass
class Chunk:
    index: int
    text: str
    page_number: Optional[int] = None


def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _find_break(text: str, end: int, min_pos: int) -> int:
    """Prefer to cut at a paragraph, line, sentence or word boundary."""
    for sep in _SEPARATORS:
        pos = text.rfind(sep, min_pos, end)
        if pos != -1:
            return pos + len(sep)
    return end


def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    if chunk_size < 200:
        raise ValueError("chunk_size must be at least 200")
    if not 0 <= overlap < chunk_size // 2:
        raise ValueError("overlap must be between 0 and half of chunk_size")

    text = _clean(text)
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    pieces: List[str] = []
    start, length = 0, len(text)
    while start < length:
        end = min(start + chunk_size, length)
        if end == length:
            cut = end
        else:
            cut = _find_break(text, end, start + int(chunk_size * 0.6))
        piece = text[start:cut].strip()
        if piece:
            pieces.append(piece)
        if cut >= length:
            break
        start = cut - overlap
        space = text.find(" ", start, cut)
        if space != -1:
            start = space + 1
    return pieces


def chunk_sections(sections: Iterable[ParsedSection],
                   chunk_size: int = CHUNK_SIZE,
                   overlap: int = CHUNK_OVERLAP) -> List[Chunk]:
    chunks: List[Chunk] = []
    for section in sections:
        for piece in split_text(section.text, chunk_size, overlap):
            chunks.append(Chunk(index=len(chunks), text=piece, page_number=section.page_number))
    return chunks