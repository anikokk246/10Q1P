import os
import json
import re
from typing import Tuple, Optional
from pydantic import BaseModel, Field
from google import genai

from subagents.database.models.schemas import DDLTaskInput, DDLTaskOutput, TableStatus
from subagents.database.tools import (
    get_connection,
    fetch_table_status,
    validate_ddl_dry_run,
    execute_ddl_committed,
)


class LLMDDLResponse(BaseModel):
    sql: str = Field(description="Exact PostgreSQL DDL statements to execute.")
    explanation: str = Field(description="Short human-readable summary of the DDL changes made.")


class DDLWorkerAgent:
    """
    Specialist Worker Agent: Responsible for end-to-end PostgreSQL DDL operations.
    1. Inspects table existence & columns
    2. Prompts Gemini with grounded schema context
    3. Runs dry-run validation (with self-healing loop on syntax error)
    4. Executes inside committed transaction
    5. Returns before & after schema status
    """

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = (
            model_name
            or os.environ.get("GEMINI_MODEL")
            or "gemini-3.8-flash"
        )

    def _get_llm_client(self) -> genai.Client:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set. Please provide it in .env or as an argument.")
        return genai.Client(api_key=self.api_key)

    def _build_prompt(
        self,
        task_input: DDLTaskInput,
        status: TableStatus,
        previous_error: Optional[str] = None,
    ) -> str:
        qualified_name = f'"{task_input.schema_name}"."{task_input.table_name}"'

        prompt_parts = [
            f"You are an expert PostgreSQL Database Architect and DDL Engineer.",
            f"Your task is to generate PostgreSQL DDL statements for the target: {qualified_name}.",
            f"\n### Database Context:",
            f"- Target Schema: {task_input.schema_name}",
            f"- Target Object: {task_input.object_type}",
            f"- Target Table Name: {task_input.table_name}",
            f"- Table Currently Exists in Database: {'YES' if status.exists else 'NO'}",
        ]

        if status.exists:
            cols_summary = [
                f"  - {col.name} ({col.data_type}, nullable={col.is_nullable}, default={col.default_value})"
                for col in status.columns
            ]
            prompt_parts.extend([
                f"\n### Current Existing Table Definition:",
                f"- Columns:\n" + ("\n".join(cols_summary) if cols_summary else "  (none)"),
                f"- Primary Keys: {status.primary_keys or 'None'}",
                f"- Existing Indexes: {status.indexes or 'None'}",
                f"\n### Modification Rule:",
                f"- The table ALREADY EXISTS. DO NOT drop or recreate the table.",
                f"- Generate only the minimal, necessary `ALTER TABLE {qualified_name}` statements to implement the requested instructions.",
                f"- Use `ADD COLUMN IF NOT EXISTS` where appropriate.",
                f"- If adding an index, use `CREATE INDEX IF NOT EXISTS ...`.",
            ])
        else:
            prompt_parts.extend([
                f"\n### Creation Rule:",
                f"- The table DOES NOT exist yet.",
                f"- Generate a standard PostgreSQL `CREATE TABLE IF NOT EXISTS {qualified_name} (...)` statement.",
                f"- Include primary keys, appropriate column types (e.g. UUID, BIGINT, TEXT, TIMESTAMPTZ, JSONB), foreign keys, check constraints, and defaults based on instructions.",
                f"- If indexes are needed, generate `CREATE INDEX IF NOT EXISTS ...` after the table creation.",
            ])

        prompt_parts.extend([
            f"\n### User Table Instructions:",
            f"{task_input.table_instructions}",
        ])

        if previous_error:
            prompt_parts.extend([
                f"\n### PREVIOUS DRY-RUN EXECUTION ERROR:",
                f"The previous attempt failed in PostgreSQL with this exact error:",
                f"--> {previous_error}",
                f"Please fix the SQL to resolve this error completely.",
            ])

        prompt_parts.extend([
            f"\n### Output Requirements:",
            f"Return a JSON object containing:",
            f"1. `sql`: The exact PostgreSQL DDL statements ready for direct execution (no markdown fences).",
            f"2. `explanation`: A concise summary of what was generated/altered.",
        ])

        return "\n".join(prompt_parts)

    def _generate_sql(
        self,
        task_input: DDLTaskInput,
        status: TableStatus,
        previous_error: Optional[str] = None,
    ) -> Tuple[str, str]:
        client = self._get_llm_client()
        prompt = self._build_prompt(task_input, status, previous_error)

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": LLMDDLResponse,
                },
            )
            data = json.loads(response.text)
            return data.get("sql", "").strip(), data.get("explanation", "").strip()
        except Exception:
            # Fallback text parsing
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt + "\nReturn strictly JSON with keys 'sql' and 'explanation'.",
            )
            text = response.text.strip()
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if match:
                text = match.group(1).strip()
            try:
                data = json.loads(text)
                return data.get("sql", "").strip(), data.get("explanation", "").strip()
            except Exception:
                return text, "Generated PostgreSQL DDL"

    def execute(self, task_input: DDLTaskInput, max_retries: int = 2) -> DDLTaskOutput:
        """Executes the complete DDL worker pipeline."""
        try:
            with get_connection(task_input.database_url) as conn:
                # Step 1: Pre-flight Inspection
                initial_status = fetch_table_status(
                    conn, task_input.schema_name, task_input.table_name
                )

                # Step 2: LLM Synthesis + Dry-Run Validation with Retry Loop
                last_error = None
                sql_to_execute = ""
                explanation = ""

                for attempt in range(max_retries + 1):
                    sql_to_execute, explanation = self._generate_sql(
                        task_input=task_input,
                        status=initial_status,
                        previous_error=last_error,
                    )

                    # Validate inside dry-run transaction
                    is_valid, validation_error = validate_ddl_dry_run(conn, sql_to_execute)
                    if is_valid:
                        break
                    last_error = validation_error

                if last_error:
                    return DDLTaskOutput(
                        success=False,
                        action="NO_OP",
                        schema_name=task_input.schema_name,
                        table_name=task_input.table_name,
                        generated_sql=sql_to_execute,
                        explanation=f"Dry-run validation failed after {max_retries} correction attempts.",
                        before_columns=initial_status.columns,
                        after_columns=initial_status.columns,
                        error=last_error,
                    )

                # Step 3: Committed Execution
                execute_ddl_committed(conn, sql_to_execute)

                # Step 4: Verification
                updated_status = fetch_table_status(
                    conn, task_input.schema_name, task_input.table_name
                )
                action = "ALTERED_TABLE" if initial_status.exists else "CREATED_TABLE"

                return DDLTaskOutput(
                    success=True,
                    action=action,
                    schema_name=task_input.schema_name,
                    table_name=task_input.table_name,
                    generated_sql=sql_to_execute,
                    explanation=explanation,
                    before_columns=initial_status.columns,
                    after_columns=updated_status.columns,
                )

        except Exception as e:
            return DDLTaskOutput(
                success=False,
                action="NO_OP",
                schema_name=task_input.schema_name,
                table_name=task_input.table_name,
                generated_sql="",
                explanation="Failed during execution.",
                error=str(e),
            )
