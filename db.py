import psycopg
from typing import Tuple, Optional
from models import TableStatus, ColumnInfo


def get_connection(db_url: str) -> psycopg.Connection:
    """Connects to PostgreSQL (including Neon with SSL) using psycopg."""
    return psycopg.connect(db_url, autocommit=False)


def fetch_table_status(conn: psycopg.Connection, schema_name: str, table_name: str) -> TableStatus:
    """Inspects PostgreSQL to check if the table exists and retrieves its schema details."""
    with conn.cursor() as cur:
        # 1. Check if table exists
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
            );
            """,
            (schema_name, table_name),
        )
        exists = cur.fetchone()[0]

        if not exists:
            return TableStatus(
                exists=False,
                schema_name=schema_name,
                table_name=table_name,
                columns=[],
                primary_keys=[],
                indexes=[],
            )

        # 2. Fetch columns
        cur.execute(
            """
            SELECT 
                column_name, 
                data_type, 
                is_nullable, 
                column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position;
            """,
            (schema_name, table_name),
        )
        columns = [
            ColumnInfo(
                name=row[0],
                data_type=row[1],
                is_nullable=(row[2].upper() == "YES"),
                default_value=row[3],
            )
            for row in cur.fetchall()
        ]

        # 3. Fetch primary key columns
        cur.execute(
            """
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = %s
              AND tc.table_name = %s
            ORDER BY kcu.ordinal_position;
            """,
            (schema_name, table_name),
        )
        primary_keys = [row[0] for row in cur.fetchall()]

        # 4. Fetch indexes
        cur.execute(
            """
            SELECT indexdef
            FROM pg_indexes
            WHERE schemaname = %s AND tablename = %s;
            """,
            (schema_name, table_name),
        )
        indexes = [row[0] for row in cur.fetchall()]

        return TableStatus(
            exists=True,
            schema_name=schema_name,
            table_name=table_name,
            columns=columns,
            primary_keys=primary_keys,
            indexes=indexes,
        )


def validate_ddl(conn: psycopg.Connection, sql: str) -> Tuple[bool, Optional[str]]:
    """Dry-runs the DDL inside an ephemeral transaction (BEGIN ... ROLLBACK) to catch errors."""
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.rollback()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)


def execute_ddl(conn: psycopg.Connection, sql: str) -> None:
    """Executes the DDL inside a committed transaction."""
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
