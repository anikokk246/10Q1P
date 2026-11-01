import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from subagents.database.models import DDLTaskInput, TableStatus, ColumnInfo
from subagents.database.workers.ddl_worker import DDLWorkerAgent
from subagents.database import DatabaseSubAgent


def test_ddl_worker_prompt_create():
    worker = DDLWorkerAgent()
    task_input = DDLTaskInput(
        schema_name="public",
        table_name="products",
        table_instructions="id uuid pk, sku text unique not null, price numeric(10,2)",
    )
    status = TableStatus(
        exists=False,
        schema_name="public",
        table_name="products",
    )
    prompt = worker._build_prompt(task_input, status)
    assert "DOES NOT exist" in prompt
    assert "CREATE TABLE IF NOT EXISTS" in prompt
    assert '"public"."products"' in prompt
    print("[OK] Test prompt for CREATE passed.")


def test_ddl_worker_prompt_alter():
    worker = DDLWorkerAgent()
    task_input = DDLTaskInput(
        schema_name="public",
        table_name="products",
        table_instructions="add stock_quantity int default 0",
    )
    status = TableStatus(
        exists=True,
        schema_name="public",
        table_name="products",
        columns=[
            ColumnInfo(name="id", data_type="uuid", is_nullable=False, default_value=None),
            ColumnInfo(name="sku", data_type="text", is_nullable=False, default_value=None),
        ],
        primary_keys=["id"],
    )
    prompt = worker._build_prompt(task_input, status)
    assert "ALREADY EXISTS" in prompt
    assert "DO NOT drop or recreate" in prompt
    assert "ADD COLUMN IF NOT EXISTS" in prompt
    print("[OK] Test prompt for ALTER passed.")


def test_subagent_missing_db():
    subagent = DatabaseSubAgent()
    output = subagent.manage_table_ddl(
        schema_name="public",
        table_name="test",
        table_instructions="id int",
    )
    assert not output.success
    assert "DATABASE_URL is not set" in output.error
    print("[OK] Test DatabaseSubAgent error handling on missing DB URL passed.")


if __name__ == "__main__":
    test_ddl_worker_prompt_create()
    test_ddl_worker_prompt_alter()
    test_subagent_missing_db()
    print("\nAll modular sub-agent tests passed successfully!")
