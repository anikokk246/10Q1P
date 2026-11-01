import os
from dotenv import load_dotenv
from models import AgentInput, AgentOutput, TableStatus
from db import get_connection, fetch_table_status, validate_ddl, execute_ddl
from llm import generate_ddl_sql

load_dotenv()


class PostgresDDLAgent:
    def __init__(self, gemini_api_key: str = None, default_db_url: str = None):
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY")
        self.default_db_url = default_db_url or os.environ.get("DATABASE_URL")

    def run(self, agent_input: AgentInput, max_correction_retries: int = 2) -> AgentOutput:
        """
        Executes the full PostgreSQL DDL workflow:
        1. Connects to database
        2. Inspects existing table status
        3. Prompts LLM for exact DDL
        4. Validates via dry-run transaction (with auto-correction loop on error)
        5. Executes DDL inside transaction
        6. Re-inspects table and returns complete feedback
        """
        # 1. Resolve DB URL
        db_url = agent_input.database_url or self.default_db_url
        if not db_url:
            return AgentOutput(
                success=False,
                action="NO_OP",
                schema_name=agent_input.schema_name,
                table_name=agent_input.table_name,
                generated_sql="",
                explanation="No database URL provided and DATABASE_URL is not set in environment.",
                error="Missing DATABASE_URL",
            )

        try:
            with get_connection(db_url) as conn:
                # 2. Fetch current status of table
                initial_status = fetch_table_status(
                    conn, agent_input.schema_name, agent_input.table_name
                )

                # 3 & 4. Generate DDL and validate via Dry-Run (with retry loop)
                last_error = None
                sql_to_execute = ""
                explanation = ""

                for attempt in range(max_correction_retries + 1):
                    sql_to_execute, explanation = generate_ddl_sql(
                        agent_input=agent_input,
                        status=initial_status,
                        previous_error=last_error,
                        api_key=self.gemini_api_key,
                    )

                    # Validate SQL in ephemeral transaction (BEGIN ... ROLLBACK)
                    is_valid, validation_error = validate_ddl(conn, sql_to_execute)
                    if is_valid:
                        break

                    last_error = validation_error

                if last_error:
                    return AgentOutput(
                        success=False,
                        action="NO_OP",
                        schema_name=agent_input.schema_name,
                        table_name=agent_input.table_name,
                        generated_sql=sql_to_execute,
                        explanation=f"Failed dry-run validation after {max_correction_retries} correction attempts.",
                        before_columns=initial_status.columns,
                        after_columns=initial_status.columns,
                        error=last_error,
                    )

                # 5. Push SQL to DB (committed transaction)
                execute_ddl(conn, sql_to_execute)

                # 6. Fetch updated table status for feedback
                updated_status = fetch_table_status(
                    conn, agent_input.schema_name, agent_input.table_name
                )

                action = "ALTERED_TABLE" if initial_status.exists else "CREATED_TABLE"

                return AgentOutput(
                    success=True,
                    action=action,
                    schema_name=agent_input.schema_name,
                    table_name=agent_input.table_name,
                    generated_sql=sql_to_execute,
                    explanation=explanation,
                    before_columns=initial_status.columns,
                    after_columns=updated_status.columns,
                )

        except Exception as e:
            return AgentOutput(
                success=False,
                action="NO_OP",
                schema_name=agent_input.schema_name,
                table_name=agent_input.table_name,
                generated_sql="",
                explanation="Failed during execution.",
                error=str(e),
            )
