"""POST /ingest endpoint."""
import logging
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import MAX_UPLOAD_BYTES
from app.ingestion.parsers import ParseError
from app.ingestion.service import SourceNotFound, ingest_source, mark_failed

log = logging.getLogger("opsintel.ingest")
router = APIRouter()


@router.post("/ingest")
def ingest(source_id: UUID = Form(...), file: UploadFile = File(...)):
    # Read at most limit + 1 bytes, so an oversized file is caught without loading it all.
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        return ingest_source(source_id, file.filename or "upload", data)
    except SourceNotFound:
        raise HTTPException(status_code=404, detail="Source not found")
    except ParseError as e:
        mark_failed(source_id, str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        log.exception("Ingestion failed for source %s", source_id)
        mark_failed(source_id, "Internal error during ingestion")
        raise HTTPException(status_code=500, detail="Ingestion failed")