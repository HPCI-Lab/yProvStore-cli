import click
import json
import requests
from rich.console import Console

from commands.auth import auth
from commands.documents import documents
from commands.pids import pids
from commands.blockchain import blockchain
from commands.artifacts import artifacts
from utils.api_client import make_request

console = Console()


class GlobalOptionsGroup(click.Group):
    """Custom Group that allows global options (--api-url, --token)
    to appear anywhere in the command line, not just before the subcommand."""

    GLOBAL_OPTIONS = {'--api-url', '--token'}

    def parse_args(self, ctx, args):
        """Move global options to the front of the args list before parsing."""
        global_args = []
        remaining = []
        args = list(args)
        i = 0
        while i < len(args):
            # Handle --option value (space-separated)
            if args[i] in self.GLOBAL_OPTIONS:
                global_args.append(args[i])
                i += 1
                if i < len(args):
                    global_args.append(args[i])
                    i += 1
            # Handle --option=value (equals syntax)
            elif '=' in args[i] and args[i].split('=', 1)[0] in self.GLOBAL_OPTIONS:
                global_args.append(args[i])
                i += 1
            else:
                remaining.append(args[i])
                i += 1
        return super().parse_args(ctx, global_args + remaining)


@click.group(cls=GlobalOptionsGroup)
@click.option(
    '--api-url',
    default='http://127.0.0.1:8000',
    help='Base URL of the yProv API server.',
    envvar='YPROV_API_URL'  # Allows setting via environment variable
)
@click.option(
    '--token',
    default=None,
    help='Bearer token for authentication. Overrides the stored login token.',
    envvar='AUTHORIZATION_TOKEN'
)
@click.pass_context
def cli(ctx, api_url, token):
    """
    yProv CLI: A command-line tool for the yProv Provenance Service.

    You can set the API URL using the --api-url option or by setting
    the YPROV_API_URL environment variable.

    You can provide an external authentication token using the --token
    option or by setting the AUTHORIZATION_TOKEN environment variable.
    When set, it takes precedence over the stored login token.
    """
    # Ensure the context object exists and store the API URL
    ctx.ensure_object(dict)
    ctx.obj['API_URL'] = api_url
    ctx.obj['TOKEN_OVERRIDE'] = token

    # Track whether the token came from --token flag or env var
    token_source = ctx.get_parameter_source('token')
    if token_source == click.core.ParameterSource.ENVIRONMENT:
        ctx.obj['TOKEN_SOURCE'] = 'env'
    elif token_source == click.core.ParameterSource.COMMANDLINE:
        ctx.obj['TOKEN_SOURCE'] = 'cli'
    else:
        ctx.obj['TOKEN_SOURCE'] = None

    # If a token override is provided (via --token or env var), ensure the
    # environment variable is set so that load_token() picks it up everywhere.
    if token:
        import os
        os.environ['AUTHORIZATION_TOKEN'] = token


@cli.command()
@click.pass_context
def check(ctx):
    """Verify if the yProv server is reachable."""
    api_url = ctx.obj['API_URL']
    console.print(f"Pinging server at [cyan]{api_url}[/cyan]...")

    try:
        # Make a simple request to the root endpoint with a timeout
        response = make_request("GET", api_url, "/status", timeout=5)
        if response is None:
            console.print("❌ [bold red]Server is unreachable or did not respond as expected.[/bold red]")
            return
        response.raise_for_status()  # Raises an exception for 4xx/5xx errors
        try:
            data = response.json()
            if data.get("status") != "ok":
                console.print(f"❌ [bold red]Server is reachable but returned an unexpected status: {data.get('status')}.[/bold red]")
                return
        except json.JSONDecodeError:
            console.print("❌ [bold red]Server is reachable but did not return valid JSON.[/bold red]")
            return
        console.print("✅ [bold green]Server is reachable and responding.[/bold green]")
    except requests.exceptions.RequestException as e:
        console.print("❌ [bold red]Server is unreachable.[/bold red]")
        console.print(f"   Error: {e}")


# Add command groups to the main CLI
cli.add_command(auth)
cli.add_command(documents)
cli.add_command(pids)
cli.add_command(blockchain)
cli.add_command(artifacts)


if __name__ == '__main__':
    cli()
