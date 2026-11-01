import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from models import AgentInput, TableStatus, ColumnInfo
from llm import build_ddl_prompt
from agent import PostgresDDLAgent


def test_prompt_generation_create():
    agent_input = AgentInput(
        schema_name="public",
        table_name="users",
        table_instructions="id (uuid pk), email (text not null unique), created_at (timestamptz default now())",
    )
    status = TableStatus(
        exists=False,
        schema_name="public",
        table_name="users",
    )
    prompt = build_ddl_prompt(agent_input, status)
    assert "DOES NOT exist" in prompt
    assert "CREATE TABLE IF NOT EXISTS" in prompt
    assert '"public"."users"' in prompt
    print("[OK] Test prompt for CREATE passed.")


def test_prompt_generation_alter():
    agent_input = AgentInput(
        schema_name="public",
        table_name="users",
        table_instructions="add phone_number (text) and make status default 'active'",
    )
    status = TableStatus(
        exists=True,
        schema_name="public",
        table_name="users",
        columns=[
            ColumnInfo(name="id", data_type="uuid", is_nullable=False, default_value=None),
            ColumnInfo(name="email", data_type="text", is_nullable=False, default_value=None),
        ],
        primary_keys=["id"],
    )
    prompt = build_ddl_prompt(agent_input, status)
    assert "ALREADY EXISTS" in prompt
    assert "DO NOT drop or recreate" in prompt
    assert "ADD COLUMN IF NOT EXISTS" in prompt
    print("[OK] Test prompt for ALTER passed.")


def test_agent_missing_db():
    agent = PostgresDDLAgent()
    agent_input = AgentInput(
        schema_name="public",
        table_name="test",
        table_instructions="id int",
    )
    output = agent.run(agent_input)
    assert not output.success
    assert "Missing DATABASE_URL" in output.error
    print("[OK] Test agent graceful error handling on missing DB URL passed.")


if __name__ == "__main__":
    test_prompt_generation_create()
    test_prompt_generation_alter()
    test_agent_missing_db()
    print("\nAll unit tests passed successfully!")
