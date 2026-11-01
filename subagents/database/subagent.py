from typing import Optional, Dict, Any, List
from subagents.database.models.schemas import DDLTaskInput, DDLTaskOutput, TableStatus
from subagents.database.workers.ddl_worker import DDLWorkerAgent
from subagents.database.tools import (
    get_connection,
    list_tables_in_schema,
    fetch_table_status,
    execute_read_query,
)


class DatabaseSubAgent:
    """
    Database Domain Sub-Agent:
    Manages all database operations and coordinates specialized workers & tools.
    """

    def __init__(self, gemini_api_key: Optional[str] = None):
        self.ddl_worker = DDLWorkerAgent(gemini_api_key=gemini_api_key)

    def manage_table_ddl(
        self,
        schema_name: str,
        table_name: str,
        table_instructions: str,
        database_url: Optional[str] = None,
        as_dict: bool = False,
    ) -> DDLTaskOutput | Dict[str, Any]:
        """Delegates DDL operations (create/alter) to the specialist DDLWorkerAgent."""
        task_input = DDLTaskInput(
            database_url=database_url,
            schema_name=schema_name,
            table_name=table_name,
            table_instructions=table_instructions,
        )
        output = self.ddl_worker.execute(task_input)
        return output.model_dump() if as_dict else output

    def list_tables(
        self, schema_name: str = "public", database_url: Optional[str] = None
    ) -> List[str]:
        """Returns all tables in the specified schema."""
        with get_connection(database_url) as conn:
            return list_tables_in_schema(conn, schema_name)

    def inspect_table(
        self, schema_name: str, table_name: str, database_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Returns detailed columns, primary keys, and indexes for a table."""
        with get_connection(database_url) as conn:
            status = fetch_table_status(conn, schema_name, table_name)
            return status.model_dump()

    def run_read_query(
        self, sql_query: str, limit: int = 100, database_url: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Executes a safe read-only SELECT query."""
        with get_connection(database_url) as conn:
            return execute_read_query(conn, sql_query, limit=limit)
