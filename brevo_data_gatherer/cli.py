"""
Command-line interface for Brevo data enrichment.
"""
import sys
import json
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON
from rich.progress import Progress, SpinnerColumn, TextColumn

# Load environment variables from multiple locations
from brevo_data_gatherer.config import load_config, load_env_from_multiple_locations
load_env_from_multiple_locations()
from brevo_data_gatherer.cache.manager import CacheManager
from brevo_data_gatherer.core.brevo_client import BrevoClient
from brevo_data_gatherer.core.linkedin_client import LinkedInClient
from brevo_data_gatherer.core.web_client import WebSearchClient
from brevo_data_gatherer.core.conversations_client import ConversationsClient
from brevo_data_gatherer.core.enricher import DataEnricher

app = typer.Typer(help="Brevo CRM Data Enrichment Tool")
console = Console()


@app.command()
def enrich(
    entity_identifier: str = typer.Argument(
        ...,
        help="Entity identifier (email, contact ID, deal ID, or company ID)"
    ),
    entity_type: str = typer.Option(
        "auto",
        "--type", "-t",
        help="Entity type: contact, deal, company, or auto to detect"
    ),
    identifier_type: str = typer.Option(
        "auto",
        "--id-type", "-i",
        help="Identifier type: email, contact_id, deal_id, company_id, or auto"
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output file path (JSON format). If not specified, prints to stdout"
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Configuration file path (YAML format)"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose logging"
    ),
    no_linkedin: bool = typer.Option(
        False,
        "--no-linkedin",
        help="Disable LinkedIn enrichment"
    ),
    no_web_search: bool = typer.Option(
        False,
        "--no-web-search",
        help="Disable web search enrichment"
    ),
    pretty: bool = typer.Option(
        True,
        "--pretty/--compact",
        help="Pretty-print JSON output"
    )
):
    """
    Enrich Brevo CRM entity with data from multiple sources.

    Examples:

        # Enrich contact by email (auto-detect)
        $ brevo-enrich contact@example.com

        # Enrich deal by ID with output to file
        $ brevo-enrich 61a5ce58c5d4795761045990 --type deal -o deal_data.json

        # Enrich company without LinkedIn data
        $ brevo-enrich 61a5ce58c5d4795761045990 --type company --no-linkedin
    """
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Loading configuration...", total=None)
            config = load_config(config_file)
            progress.update(task, completed=True)

            # Validate Brevo API key
            if not config.brevo.api_key:
                console.print("[red]Error: BREVO_API_KEY not configured[/red]")
                console.print("\nPlease set your API key:")
                console.print("  export BREVO_API_KEY='your-api-key'")
                raise typer.Exit(1)

            # Initialize cache manager
            task = progress.add_task("Initializing cache...", total=None)
            cache_db_path = config.cache_dir / "cache.db"
            cache_manager = CacheManager(cache_db_path)
            progress.update(task, completed=True)

            # Initialize Brevo client
            task = progress.add_task("Connecting to Brevo API...", total=None)
            brevo_client = BrevoClient(
                api_key=config.brevo.api_key,
                base_url=config.brevo.base_url,
                cache_manager=cache_manager
            )
            progress.update(task, completed=True)

            # Initialize optional clients
            linkedin_client = None
            if not no_linkedin and config.linkedin.enabled:
                task = progress.add_task("Initializing LinkedIn integration...", total=None)
                if config.linkedin.pipedream_workflow_url:
                    linkedin_client = LinkedInClient(
                        provider=config.linkedin.provider,
                        cache_manager=cache_manager,
                        api_key=config.linkedin.api_key,
                        pipedream_workflow_url=config.linkedin.pipedream_workflow_url
                    )
                    progress.update(task, completed=True)
                else:
                    logger.warning("LinkedIn integration enabled but no workflow URL configured")
                    progress.update(task, description="LinkedIn: Not configured (skipped)")

            web_client = None
            if not no_web_search and config.web_search.enabled:
                task = progress.add_task("Initializing web search...", total=None)
                if config.web_search.api_key:
                    web_client = WebSearchClient(
                        provider=config.web_search.provider,
                        cache_manager=cache_manager,
                        api_key=config.web_search.api_key
                    )
                    progress.update(task, completed=True)
                else:
                    logger.warning("Web search enabled but no API key configured")
                    progress.update(task, description="Web search: Not configured (skipped)")

            # Initialize conversations client
            conversations_client = None
            if config.conversations.enabled:
                task = progress.add_task("Initializing conversations API...", total=None)
                if config.conversations.cookie_string:
                    conversations_client = ConversationsClient(
                        cookie_string=config.conversations.cookie_string,
                        backend_url=config.conversations.backend_url,
                        cache_manager=cache_manager
                    )
                    progress.update(task, completed=True)
                else:
                    logger.warning("Conversations enabled but no cookie configured (set BREVO_COOKIE)")
                    progress.update(task, description="Conversations: Not configured (skipped)")

            # Initialize enricher
            enricher = DataEnricher(
                brevo_client=brevo_client,
                linkedin_client=linkedin_client,
                web_client=web_client,
                conversations_client=conversations_client,
                cache_manager=cache_manager
            )

            # Perform enrichment
            task = progress.add_task(
                f"Enriching {entity_type} {entity_identifier}...",
                total=None
            )

        # Run enrichment (outside progress context for cleaner logs)
        console.print(f"\n[bold cyan]Enriching:[/bold cyan] {entity_identifier}")
        enriched_data = enricher.enrich(
            entity_identifier=entity_identifier,
            entity_type=entity_type,
            identifier_type=identifier_type
        )

        # Convert to dict for output
        output_data = enriched_data.dict()

        # Display summary
        console.print("\n[bold green]✓ Enrichment complete![/bold green]")
        console.print(Panel(
            f"[cyan]Entity Type:[/cyan] {output_data['primary_type']}\n"
            f"[cyan]API Calls:[/cyan] {output_data['metadata']['api_calls_made']}\n"
            f"[cyan]Data Quality:[/cyan] {output_data['metadata']['data_quality']}\n"
            f"[cyan]Duration:[/cyan] {output_data['metadata']['duration_ms']}ms\n"
            f"[cyan]Sources:[/cyan] {', '.join(output_data['metadata']['sources_used'])}",
            title="[bold]Enrichment Summary[/bold]",
            border_style="green"
        ))

        # Output results
        if output_file:
            # Write to file
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                if pretty:
                    json.dump(output_data, f, indent=2, default=str)
                else:
                    json.dump(output_data, f, default=str)
            console.print(f"\n[green]Output written to:[/green] {output_file}")
        else:
            # Print to stdout
            console.print("\n[bold]Enriched Data:[/bold]")
            if pretty:
                console.print(JSON(json.dumps(output_data, default=str)))
            else:
                print(json.dumps(output_data, default=str))

        # Display cache statistics
        stats = cache_manager.get_statistics()
        if stats['total_entries'] > 0:
            console.print("\n[bold]Cache Statistics:[/bold]")
            console.print(f"  Total entries: {stats['total_entries']}")
            console.print(f"  Total size: {stats['total_size_mb']:.2f} MB")
            console.print(f"  Expired entries: {stats['expired_entries']}")

    except ValueError as e:
        console.print(f"\n[red]Error:[/red] {str(e)}")
        logger.error(f"Validation error: {e}", exc_info=verbose)
        raise typer.Exit(1)

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {str(e)}")
        logger.error(f"Enrichment failed: {e}", exc_info=True)
        raise typer.Exit(1)


@app.command()
def cache_info(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Configuration file path (YAML format)"
    )
):
    """Display cache statistics and information."""
    try:
        config = load_config(config_file)
        cache_manager = CacheManager(config.cache_dir / "cache.db")

        stats = cache_manager.get_statistics()

        console.print(Panel(
            f"[cyan]Cache Directory:[/cyan] {config.cache_dir}\n"
            f"[cyan]Total Entries:[/cyan] {stats['total_entries']}\n"
            f"[cyan]Total Size:[/cyan] {stats['total_size_mb']:.2f} MB\n"
            f"[cyan]Expired Entries:[/cyan] {stats['expired_entries']}\n"
            f"[cyan]Cache Hit Rate:[/cyan] {stats.get('hit_rate', 0):.1%}",
            title="[bold]Cache Statistics[/bold]",
            border_style="cyan"
        ))

        # Show breakdown by source
        console.print("\n[bold]Entries by Source:[/bold]")
        by_source = stats.get("by_source", {})
        for source in ["brevo_crm", "brevo_notes", "brevo_tasks", "brevo_conversations", "linkedin", "web_search"]:
            count = by_source.get(source, 0)
            if count > 0:
                console.print(f"  {source}: {count}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def cache_clear(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Configuration file path (YAML format)"
    ),
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="Skip confirmation prompt"
    )
):
    """Clear all cache entries."""
    try:
        config = load_config(config_file)
        cache_manager = CacheManager(config.cache_dir / "cache.db")

        stats = cache_manager.get_statistics()

        if not force:
            confirm = typer.confirm(
                f"Clear {stats['total_entries']} cache entries "
                f"({stats['total_size_mb']:.2f} MB)?"
            )
            if not confirm:
                console.print("[yellow]Cache clear cancelled[/yellow]")
                raise typer.Exit(0)

        cache_manager.clear_all()
        console.print("[green]✓ Cache cleared successfully[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def cache_cleanup(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Configuration file path (YAML format)"
    )
):
    """Clean up expired cache entries."""
    try:
        config = load_config(config_file)
        cache_manager = CacheManager(config.cache_dir / "cache.db")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Cleaning up expired entries...", total=None)
            removed = cache_manager.cleanup_expired()
            progress.update(task, completed=True)

        console.print(f"[green]✓ Removed {removed} expired cache entries[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def init_config(
    output_path: Path = typer.Option(
        Path("config.yaml"),
        "--output", "-o",
        help="Output configuration file path"
    )
):
    """Create a default configuration file."""
    from brevo_data_gatherer.config import create_default_config_file

    try:
        if output_path.exists():
            overwrite = typer.confirm(
                f"Configuration file {output_path} already exists. Overwrite?"
            )
            if not overwrite:
                console.print("[yellow]Configuration creation cancelled[/yellow]")
                raise typer.Exit(0)

        create_default_config_file(output_path)
        console.print(f"[green]✓ Configuration file created:[/green] {output_path}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
