import sys
import argparse
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from models import AgentInput, AgentOutput
from agent import PostgresDDLAgent

load_dotenv()
console = Console()


def display_output(output: AgentOutput):
    """Renders formatted feedback for the user in the terminal."""
    if output.success:
        action_color = "bold green" if output.action == "CREATED_TABLE" else "bold cyan"
        console.print(
            Panel(
                f"[{action_color}]✔ SUCCESS: {output.action}[/{action_color}]\n"
                f"Target: [bold]{output.schema_name}.{output.table_name}[/bold]\n\n"
                f"[italic]{output.explanation}[/italic]",
                title="[bold green]PostgreSQL DDL Agent Result[/bold green]",
                border_style="green",
            )
        )

        # Show Executed SQL
        console.print("\n[bold yellow]Executed SQL Script:[/bold yellow]")
        syntax = Syntax(output.generated_sql, "sql", theme="monokai", line_numbers=True)
        console.print(syntax)

        # Show Updated Schema Table
        table = Table(
            title=f"Updated Columns for {output.schema_name}.{output.table_name}",
            border_style="blue",
        )
        table.add_column("Column Name", style="cyan", no_wrap=True)
        table.add_column("Data Type", style="magenta")
        table.add_column("Nullable", style="green")
        table.add_column("Default Value", style="white")

        for col in output.after_columns:
            table.add_row(
                col.name,
                col.data_type,
                "YES" if col.is_nullable else "NO",
                col.default_value or "None",
            )

        console.print("\n", table)

    else:
        console.print(
            Panel(
                f"[bold red]✘ FAILED[/bold red]\n"
                f"Target: [bold]{output.schema_name}.{output.table_name}[/bold]\n"
                f"Error: {output.error}\n\n"
                f"[italic]{output.explanation}[/italic]",
                title="[bold red]PostgreSQL DDL Agent Failure[/bold red]",
                border_style="red",
            )
        )
        if output.generated_sql:
            console.print("\n[bold yellow]Attempted SQL:[/bold yellow]")
            syntax = Syntax(output.generated_sql, "sql", theme="monokai", line_numbers=True)
            console.print(syntax)


def main():
    parser = argparse.ArgumentParser(
        description="AI Agent that connects to PostgreSQL and performs DDL operations safely."
    )
    parser.add_argument("--url", help="PostgreSQL connection string (defaults to DATABASE_URL in .env)")
    parser.add_argument("--schema", help="Target PostgreSQL schema (e.g. public)")
    parser.add_argument("--table", help="Target table name")
    parser.add_argument("--instructions", help="Text instructions for columns and constraints")

    args = parser.parse_args()

    console.print(
        Panel.fit(
            "[bold cyan]PostgreSQL DDL AI Agent[/bold cyan]\n"
            "Inspects existing schema -> LLM Generates DDL -> Dry-Run Validation -> Transactional Execution",
            border_style="cyan",
        )
    )

    # Interactive input if flags not provided
    schema_name = args.schema
    while not schema_name:
        schema_name = console.input("[bold yellow]Enter Schema Name (e.g. public): [/bold yellow]").strip()

    table_name = args.table
    while not table_name:
        table_name = console.input("[bold yellow]Enter Table Name: [/bold yellow]").strip()

    instructions = args.instructions
    while not instructions:
        instructions = console.input(
            "[bold yellow]Enter Table Instructions (columns, types, constraints): [/bold yellow]"
        ).strip()

    agent_input = AgentInput(
        database_url=args.url,
        schema_name=schema_name,
        table_name=table_name,
        table_instructions=instructions,
    )

    console.print(f"\n[cyan]Inspecting {schema_name}.{table_name} in database and consulting LLM...[/cyan]\n")

    agent = PostgresDDLAgent()
    output = agent.run(agent_input)

    display_output(output)


if __name__ == "__main__":
    main()
