"""
example_parent_agent.py

Demonstrates how a Main Agent or Orchestrator script imports and invokes
the Database Sub-Agent and its DDL Worker Agent.
"""

from subagents.database import DatabaseSubAgent


def run_parent_agent_workflow():
    print("--- Main Orchestrator Agent Workflow Started ---")

    # The Main Agent initializes the Database Sub-Agent
    db_agent = DatabaseSubAgent()

    print("\n[Main Agent] Requesting Database Sub-Agent to create/alter 'audit_logs' table...")

    result = db_agent.manage_table_ddl(
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
        as_dict=True,
    )

    if result["success"]:
        print(f"[Main Agent] Sub-Agent completed task successfully!")
        print(f"Action Taken: {result['action']}")
        print(f"Executed SQL:\n{result['generated_sql']}")
        print(f"Explanation: {result['explanation']}")
    else:
        print(f"[Main Agent] Sub-Agent reported failure!")
        print(f"Error: {result['error']}")

    print("\n--- Main Orchestrator Agent Workflow Finished ---")


if __name__ == "__main__":
    run_parent_agent_workflow()
