import json
from typing import Optional
from subagents.database.subagent import DatabaseSubAgent
from subagents.database.models.schemas import DDLTaskInput, DDLTaskOutput

__all__ = ["DatabaseSubAgent", "register_database_mcp"]


def register_database_mcp(mcp_server):
    """
    Registers the Database Sub-Agent and its specialized worker agents & tools
    onto the provided FastMCP server instance.
    """
    db_subagent = DatabaseSubAgent()

    # --- 1. WORKER AGENT TOOL (Intelligent DDL Agent) ---
    @mcp_server.tool()
    def postgres_manage_table_ddl(
        schema_name: str,
        table_name: str,
        table_instructions: str,
        database_url: Optional[str] = None,
    ) -> str:
        """
        Specialist DDL Worker Agent:
        Introspects target PostgreSQL database to check if table exists.
        Synthesizes optimal CREATE or ALTER DDL using Gemini.
        Runs a dry-run transaction test to self-heal any SQL errors.
        Executes inside a committed transaction and returns verified schema diff.
        """
        result = db_subagent.manage_table_ddl(
            schema_name=schema_name,
            table_name=table_name,
            table_instructions=table_instructions,
            database_url=database_url,
            as_dict=True,
        )
        return json.dumps(result, indent=2)

    # --- 2. DETERMINISTIC TOOLS (Direct DB Primitives) ---
    @mcp_server.tool()
    def postgres_list_tables(
        schema_name: str = "public", database_url: Optional[str] = None
    ) -> str:
        """Deterministic Tool: Directly lists all table names in a PostgreSQL schema without using an LLM."""
        tables = db_subagent.list_tables(schema_name=schema_name, database_url=database_url)
        return json.dumps({"schema": schema_name, "tables": tables}, indent=2)

    @mcp_server.tool()
    def postgres_inspect_table(
        schema_name: str, table_name: str, database_url: Optional[str] = None
    ) -> str:
        """Deterministic Tool: Retrieves column types, nullability, defaults, primary keys, and indexes for a table."""
        metadata = db_subagent.inspect_table(
            schema_name=schema_name, table_name=table_name, database_url=database_url
        )
        return json.dumps(metadata, indent=2)

    @mcp_server.tool()
    def postgres_read_query(
        sql_query: str, limit: int = 100, database_url: Optional[str] = None
    ) -> str:
        """Deterministic Tool: Executes a safe read-only SELECT query against PostgreSQL with row limit enforcement."""
        results = db_subagent.run_read_query(
            sql_query=sql_query, limit=limit, database_url=database_url
        )
        return json.dumps(results, indent=2, default=str)
