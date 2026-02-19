import click
from rich.console import Console
from rich.table import Table

from utils.api_client import make_request


console = Console()


@click.group(name="related")
def related():
    """
    Manage related PIDs for artifacts.

    Related PIDs are stored in the artifact PID record under `related_pids`.
    """
    pass


@related.command(name="list")
@click.argument("pid")
@click.pass_context
def list_related(ctx, pid):
    """List related PIDs for an artifact."""
    api_url = ctx.obj["API_URL"]

    response = make_request("GET", api_url, f"/artifacts/{pid}/related")
    if not response:
        console.print("[red]❌ Failed to retrieve related PIDs[/red]")
        return

    if response.status_code != 200:
        console.print(f"❌ [bold red]Error {response.status_code}:[/bold red] {response.text}")
        return

    data = response.json()
    related_pids = data.get("related_pids", [])

    if not related_pids:
        console.print(f"[yellow]No related PIDs set for artifact '{pid}'.[/yellow]")
        return

    table = Table(title=f"Related PIDs for Artifact {pid}")
    table.add_column("#", style="magenta")
    table.add_column("Related PID", style="cyan")

    for idx, related_pid in enumerate(related_pids, start=1):
        table.add_row(str(idx), related_pid)

    console.print(table)


@related.command(name="add")
@click.argument("pid")
@click.option(
    "--related-pid",
    "related_pids",
    multiple=True,
    required=True,
    help="PID to add as related. Can be provided multiple times.",
)
@click.pass_context
def add_related(ctx, pid, related_pids):
    """Add one or more related PIDs to an artifact."""
    api_url = ctx.obj["API_URL"]

    normalized_related_pids: list[str] = []
    seen = set()
    for value in related_pids:
        for part in value.split(","):
            candidate = part.strip()
            if not candidate:
                continue
            if candidate not in seen:
                normalized_related_pids.append(candidate)
                seen.add(candidate)

    if not normalized_related_pids:
        console.print("[red]❌ No valid related PIDs provided.[/red]")
        return

    payload = {"related_pids": normalized_related_pids}
    response = make_request("PATCH", api_url, f"/artifacts/{pid}/related", json=payload)

    if not response:
        console.print("[red]❌ Failed to update related PIDs[/red]")
        return

    if response.status_code != 200:
        console.print(f"❌ [bold red]Error {response.status_code}:[/bold red] {response.text}")
        return

    data = response.json()
    console.print("✅ [bold green]Related PIDs updated successfully![/bold green]")
    console.print_json(data=data)
