import os
import json
import re
from typing import Tuple, Optional
from pydantic import BaseModel, Field
from google import genai
from models import AgentInput, TableStatus


class LLMDDLResponse(BaseModel):
    sql: str = Field(description="Exact PostgreSQL DDL statements to execute.")
    explanation: str = Field(description="Short human-readable summary of the DDL changes made.")


def get_gemini_client(api_key: Optional[str] = None) -> genai.Client:
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Please provide it in .env or pass it as an argument."
        )
    return genai.Client(api_key=key)


def build_ddl_prompt(
    agent_input: AgentInput,
    status: TableStatus,
    previous_error: Optional[str] = None,
) -> str:
    qualified_name = f'"{agent_input.schema_name}"."{agent_input.table_name}"'

    prompt_parts = [
        f"You are an expert PostgreSQL Database Architect and DDL Engineer.",
        f"Your task is to generate PostgreSQL DDL statements for the target: {qualified_name}.",
        f"\n### Database Context:",
        f"- Target Schema: {agent_input.schema_name}",
        f"- Target Object: {agent_input.object_type}",
        f"- Target Table Name: {agent_input.table_name}",
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
        f"{agent_input.table_instructions}",
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


def generate_ddl_sql(
    agent_input: AgentInput,
    status: TableStatus,
    previous_error: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.5-flash",
) -> Tuple[str, str]:
    """Interacts with Gemini to generate exact PostgreSQL DDL based on current table status and instructions."""
    client = get_gemini_client(api_key)
    prompt = build_ddl_prompt(agent_input, status, previous_error)

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": LLMDDLResponse,
            },
        )
        data = json.loads(response.text)
        return data.get("sql", "").strip(), data.get("explanation", "").strip()
    except Exception as e:
        # Fallback without schema constraint if needed
        response = client.models.generate_content(
            model=model_name,
            contents=prompt + "\nReturn strictly JSON with keys 'sql' and 'explanation'.",
        )
        text = response.text.strip()
        # Extract json block if wrapped in markdown
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1).strip()
        try:
            data = json.loads(text)
            return data.get("sql", "").strip(), data.get("explanation", "").strip()
        except Exception:
            # If still fails to parse JSON, return text as SQL
            return text, "Generated PostgreSQL DDL"
