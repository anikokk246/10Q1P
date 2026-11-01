import psycopg
from typing import List, Dict, Any
from subagents.database.models.schemas import TableStatus, ColumnInfo


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


def list_tables_in_schema(conn: psycopg.Connection, schema_name: str = "public") -> List[str]:
    """Returns a list of all table names in a specified schema."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
            ORDER BY table_name;
            """,
            (schema_name,),
        )
        return [row[0] for row in cur.fetchall()]
