import os
import psycopg
from typing import Optional


def get_connection(db_url: Optional[str] = None) -> psycopg.Connection:
    """Connects to PostgreSQL (supports local Docker and Neon SSL)."""
    resolved_url = db_url or os.environ.get("DATABASE_URL")
    if not resolved_url:
        raise ValueError("DATABASE_URL is not set. Please provide it in .env or as an argument.")
    return psycopg.connect(resolved_url, autocommit=False)
