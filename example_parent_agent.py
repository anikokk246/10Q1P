"""
example_parent_agent.py

Demonstrates how another Python agent or script calls the PostgreSQL DDL AI Agent.
"""

from agent import execute_ddl_task, PostgresDDLAgent
from models import AgentInput


def run_parent_agent_workflow():
    print("--- Parent Agent Workflow Started ---")

    # Example 1: Direct function call (simplest integration)
    # The parent agent wants to ensure an 'audit_logs' table exists
    print("\n[Parent Agent] Requesting creation/update of 'audit_logs' table...")

    result = execute_ddl_task(
        schema_name="public",
        table_name="audit_logs",
        table_instructions="""
        id bigserial primary key,
        actor_id uuid not null,
        action text not null,
        metadata jsonb default '{}'::jsonb,
        created_at timestamptz default now(),
        index on actor_id,
        index on created_at
        """,
        as_dict=True,  # Set to True to get a standard Python dictionary
    )

    if result["success"]:
        print(f"[Parent Agent] Operation Success!")
        print(f"Action Taken: {result['action']}")
        print(f"Executed SQL:\n{result['generated_sql']}")
        print(f"Explanation: {result['explanation']}")
    else:
        print(f"[Parent Agent] Operation Failed!")
        print(f"Error: {result['error']}")

    print("\n--- Parent Agent Workflow Finished ---")


if __name__ == "__main__":
    run_parent_agent_workflow()
