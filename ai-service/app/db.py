"""Database connection helper."""
import psycopg

from app.config import DATABASE_URL


def connect() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL, connect_timeout=5)