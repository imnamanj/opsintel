"""Ingestion pipeline: file bytes -> parse -> chunk -> embed -> store."""
import hashlib
import tempfile
import time
from pathlib import Path
from uuid import UUID

from app.db import connect
from app.ingestion.chunker import chunk_sections
from app.ingestion.embedder import MODEL_NAME, embed_texts
from app.ingestion.parsers import ParseError, parse_file


class SourceNotFound(Exception):
    """No data_sources row exists for this source_id."""


def _vector_literal(vec) -> str:
    """pgvector accepts text like '[0.1,0.2,...]' with a ::vector cast."""
    return "[" + ",".join(str(float(x)) for x in vec) + "]"


def _get_source_type(source_id: UUID) -> str:
    with connect() as conn:
        row = conn.execute(
            "select type from data_sources where id = %s", (source_id,)
        ).fetchone()
    if row is None:
        raise SourceNotFound(str(source_id))
    return row[0]


def mark_failed(source_id: UUID, message: str) -> None:
    """Record a failed ingestion in its own small transaction."""
    with connect() as conn:
        conn.execute(
            "update data_sources set status = 'FAILED', error_message = %s "
            "where id = %s",
            (message[:500], source_id),
        )


def ingest_source(source_id: UUID, filename: str, data: bytes) -> dict:
    # The file type comes from the database, never from the client.
    file_type = _get_source_type(source_id)
    ms = {}

    # 1. Parse (parsers need a Path, so write bytes to a temp file first)
    t = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"upload.{file_type.lower()}"
        path.write_bytes(data)
        sections = list(parse_file(path, file_type))
    ms["parse"] = (time.perf_counter() - t) * 1000
    if not sections:
        raise ParseError("No text found in file")

    # 2. Chunk
    t = time.perf_counter()
    chunks = list(chunk_sections(sections))
    ms["chunk"] = (time.perf_counter() - t) * 1000
    if not chunks:
        raise ParseError("No chunks produced from file")

    # 3. Embed
    t = time.perf_counter()
    vectors = embed_texts([c.text for c in chunks])
    ms["embed"] = (time.perf_counter() - t) * 1000

    pages = [s.page_number for s in sections if s.page_number]
    page_count = max(pages) if pages else None
    checksum = hashlib.sha256(data).hexdigest()

    rows = [
        (c.index, c.text, c.page_number, _vector_literal(v), MODEL_NAME)
        for c, v in zip(chunks, vectors)
    ]

    # 4. Store: one transaction. Any error means rollback, nothing half-written.
    t = time.perf_counter()
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("delete from documents where source_id = %s", (source_id,))
            replaced = cur.rowcount
            cur.execute(
                "insert into documents (source_id, title, checksum, page_count) "
                "values (%s, %s, %s, %s) returning id",
                (source_id, filename, checksum, page_count),
            )
            document_id = cur.fetchone()[0]
            cur.executemany(
                "insert into document_chunks "
                "(document_id, chunk_index, content, page_number, embedding, embedding_model) "
                "values (%s, %s, %s, %s, %s::vector, %s)",
                [(document_id, *r) for r in rows],
            )
            cur.execute(
                "update data_sources set status = 'READY', error_message = null "
                "where id = %s",
                (source_id,),
            )
    ms["store"] = (time.perf_counter() - t) * 1000

    return {
        "source_id": str(source_id),
        "document_id": str(document_id),
        "file_type": file_type,
        "chunks": len(chunks),
        "page_count": page_count,
        "replaced_documents": replaced,
        "embedding_model": MODEL_NAME,
        "timings_ms": {k: round(v, 1) for k, v in ms.items()},
    }