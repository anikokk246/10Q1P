import os
import sys
import argparse
from dotenv import load_dotenv
from rich.console import Console

from chat import start_chat
from subagents.database import DatabaseSubAgent
from subagents.database.models import DDLTaskOutput

load_dotenv()
console = Console()


def run_one_off_cli(args):
    """Runs a single DDL operation without entering chat mode."""
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.table import Table

    db_subagent = DatabaseSubAgent(model_name=args.model)
    output = db_subagent.manage_table_ddl(
        schema_name=args.schema or "public",
        table_name=args.table,
        table_instructions=args.instructions,
        database_url=args.url,
    )

    if output.success:
        action_color = "bold green" if output.action == "CREATED_TABLE" else "bold cyan"
        console.print(
            Panel(
                f"[{action_color}]✔ SUCCESS: {output.action}[/{action_color}]\n"
                f"Target: [bold]{output.schema_name}.{output.table_name}[/bold]\n\n"
                f"[italic]{output.explanation}[/italic]",
                title="[bold green]Database Worker Agent Result[/bold green]",
                border_style="green",
            )
        )
        syntax = Syntax(output.generated_sql, "sql", theme="monokai", line_numbers=True)
        console.print(syntax)
    else:
        console.print(
            Panel(
                f"[bold red]✘ FAILED[/bold red]\n"
                f"Target: [bold]{output.schema_name}.{output.table_name}[/bold]\n"
                f"Error: {output.error}",
                title="[bold red]Database Worker Agent Failure[/bold red]",
                border_style="red",
            )
        )


def main():
    default_model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

    parser = argparse.ArgumentParser(
        description="HUMAN > MAIN AGENT > SUB-AGENTS > WORKER AGENTS > TOOLS"
    )
    parser.add_argument("--url", help="PostgreSQL connection string (defaults to DATABASE_URL in .env)")
    parser.add_argument("--schema", help="Target PostgreSQL schema (e.g. public)")
    parser.add_argument("--table", help="Target table name (if running in one-off mode)")
    parser.add_argument("--instructions", help="Text instructions for columns and constraints")
    parser.add_argument("--model", default=default_model, help=f"Gemini model name (default: {default_model})")

    args = parser.parse_args()

    # If --table was passed, run one-off mode; otherwise default to interactive CHAT mode!
    if args.table:
        run_one_off_cli(args)
    else:
        start_chat()


if __name__ == "__main__":
    main()
