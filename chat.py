"""
chat.py - Interactive Human <-> Main Agent Chat Interface

Implements the top layer of our architecture:
HUMAN > MAIN AGENT > SUB-AGENTS > WORKER AGENTS > TOOLS

The Human chats naturally in plain English with the Main Agent.
The Main Agent uses autonomous tool calling to dispatch work to our
Database Sub-Agent and Worker Agents!
"""

import os
import json
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from google import genai
from google.genai import types

from subagents.database import DatabaseSubAgent

load_dotenv()
console = Console()

# Initialize Database Sub-Agent
db_subagent = DatabaseSubAgent()


# --- TOOLS PROVIDED TO THE MAIN AGENT ---
def postgres_manage_table_ddl(
    schema_name: str, table_name: str, table_instructions: str
) -> str:
    """
    Creates a new database table or modifies an existing table in PostgreSQL.
    Use this whenever the user wants to create, add columns to, or alter a database table.
    
    Args:
        schema_name: The PostgreSQL schema name (defaults to 'public').
        table_name: The target table name (e.g. 'users', 'orders', 'books').
        table_instructions: Description of the columns, data types, primary keys, or changes requested.
    """
    console.print(
        f"\n  [dim cyan]⚡ [Main Agent] Delegating to Database Sub-Agent: "
        f"[bold]manage_table_ddl[/bold](table='{schema_name}.{table_name}')[/dim cyan]"
    )
    result = db_subagent.manage_table_ddl(
        schema_name=schema_name,
        table_name=table_name,
        table_instructions=table_instructions,
        as_dict=True,
    )
    if result.get("success"):
        console.print(
            f"  [dim green]✔ [Database Sub-Agent] Successfully executed: {result.get('action')}[/dim green]\n"
        )
    else:
        console.print(
            f"  [dim red]✘ [Database Sub-Agent] Failed: {result.get('error')}[/dim red]\n"
        )
    return json.dumps(result, indent=2)


def postgres_list_tables(schema_name: str = "public") -> str:
    """
    Lists all tables existing in the database schema.
    Use this when the user asks what tables exist or to list tables.
    """
    console.print(
        f"\n  [dim cyan]⚡ [Main Agent] Delegating to Database Sub-Agent: [bold]list_tables[/bold]('{schema_name}')[/dim cyan]"
    )
    tables = db_subagent.list_tables(schema_name=schema_name)
    return json.dumps({"schema": schema_name, "tables": tables}, indent=2)


def postgres_inspect_table(schema_name: str, table_name: str) -> str:
    """
    Inspects an existing table and returns its column names, data types, and primary keys.
    Use this when the user asks about the columns or structure of a specific table.
    """
    console.print(
        f"\n  [dim cyan]⚡ [Main Agent] Delegating to Database Sub-Agent: [bold]inspect_table[/bold]('{schema_name}.{table_name}')[/dim cyan]"
    )
    metadata = db_subagent.inspect_table(schema_name=schema_name, table_name=table_name)
    return json.dumps(metadata, indent=2)


def postgres_read_query(sql_query: str) -> str:
    """
    Executes a read-only SELECT query against PostgreSQL and returns results.
    Use this when the user asks to see records or data stored in a table.
    """
    console.print(
        f"\n  [dim cyan]⚡ [Main Agent] Delegating to Database Sub-Agent: [bold]read_query[/bold][/dim cyan]"
    )
    results = db_subagent.run_read_query(sql_query=sql_query, limit=50)
    return json.dumps(results, indent=2, default=str)


def start_chat():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        console.print(
            "[bold red]Error: GEMINI_API_KEY is not set. Please export it or put it in .env.[/bold red]"
        )
        return

    model_name = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    client = genai.Client(api_key=api_key)

    system_prompt = (
        "You are the Main Orchestrator Agent (Jack of All Trades).\n"
        "You talk directly with the human user in natural, friendly, helpful English.\n"
        "When the user wants to create, modify, inspect, or query a database table, you do NOT "
        "write or execute raw SQL yourself. Instead, you delegate by calling the appropriate "
        "Database Sub-Agent tool (e.g. postgres_manage_table_ddl, postgres_list_tables, postgres_inspect_table).\n"
        "If the user gives brief instructions like 'create a table for customer orders', you decide a sensible "
        "table name (e.g. 'customer_orders') and provide rich, helpful column specifications to the tool.\n"
        "After the tool returns, summarize the outcome clearly for the human."
    )

    chat = client.chats.create(
        model=model_name,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[
                postgres_manage_table_ddl,
                postgres_list_tables,
                postgres_inspect_table,
                postgres_read_query,
            ],
            temperature=0.7,
        ),
    )

    console.print(
        Panel.fit(
            f"[bold green]HUMAN ──► MAIN AGENT (Chat Mode)[/bold green]\n"
            f"Model: [bold yellow]{model_name}[/bold yellow] | Tools: [cyan]Database Sub-Agent Suite[/cyan]\n"
            f"[dim]Type your message naturally (e.g., 'Can you create a table for books?'). Type 'exit' to quit.[/dim]",
            border_style="green",
        )
    )

    while True:
        try:
            user_input = console.input("\n[bold yellow]You:[/bold yellow] ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                console.print("[dim]Goodbye![/dim]")
                break

            # Send message to Main Agent (with automatic tool calling)
            response = chat.send_message(user_input)

            # Print Main Agent's conversational response
            console.print("\n[bold green]Main Agent:[/bold green]")
            console.print(Markdown(response.text or "(Action completed)"))

        except KeyboardInterrupt:
            console.print("\n[dim]Session ended.[/dim]")
            break
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}")


if __name__ == "__main__":
    start_chat()
