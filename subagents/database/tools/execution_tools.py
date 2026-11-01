import psycopg
from typing import Tuple, Optional, List, Dict, Any


def validate_ddl_dry_run(conn: psycopg.Connection, sql: str) -> Tuple[bool, Optional[str]]:
    """Dry-runs the DDL inside an ephemeral transaction (BEGIN ... ROLLBACK) to catch errors."""
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.rollback()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)


def execute_ddl_committed(conn: psycopg.Connection, sql: str) -> None:
    """Executes the DDL inside a committed transaction."""
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def execute_read_query(
    conn: psycopg.Connection, sql: str, limit: int = 100
) -> List[Dict[str, Any]]:
    """Executes a safe read-only SELECT query and returns records as dictionaries."""
    # Ensure read-only transaction
    with conn.cursor() as cur:
        cur.execute("SET TRANSACTION READ ONLY;")
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchmany(limit)
        return [dict(zip(columns, row)) for row in rows]
