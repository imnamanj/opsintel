"""Settings for the AI service."""
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://opsintel:opsintel_dev@localhost:5432/opsintel",
)
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
ALLOWED_TYPES = {"PDF", "TXT", "CSV"}