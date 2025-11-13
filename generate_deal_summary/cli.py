"""
CLI interface for deal summarization.
"""
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from generate_deal_summary.core import AIClient, DealSummarizer
from generate_deal_summary.utils.prompt_loader import PromptLoader
from generate_deal_summary.models import DealSummary
from generate_deal_summary.cache import SummaryCache

# Import Script 1 for enrichment
try:
    from brevo_data_gatherer.config import load_config
    from brevo_data_gatherer.cache.manager import CacheManager
    from brevo_data_gatherer.core.brevo_client import BrevoClient
    from brevo_data_gatherer.core.conversations_client import ConversationsClient
    from brevo_data_gatherer.core.enricher import DataEnricher
    SCRIPT1_AVAILABLE = True
except ImportError:
    SCRIPT1_AVAILABLE = False

app = typer.Typer(
    help="AI-Powered Deal Summarization Tool with Intelligent Caching",
    add_completion=False
)
console = Console()

# Default cache directory
DEFAULT_CACHE_DIR = Path.home() / ".brevo_sales_agent" / "summary_cache"


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@app.command()
def summarize(
    input_file: Optional[Path] = typer.Argument(
        None,
        help="Path to enriched data JSON file from Script 1 (optional if using --deal-id/--contact-id/--company-id)",
        exists=True
    ),
    # Entity enrichment options (alternative to input_file)
    deal_id: Optional[str] = typer.Option(
        None,
        "--deal-id",
        help="Deal ID to enrich and summarize"
    ),
    contact_id: Optional[str] = typer.Option(
        None,
        "--contact-id",
        help="Contact ID to enrich and summarize"
    ),
    contact_email: Optional[str] = typer.Option(
        None,
        "--contact-email",
        help="Contact email to enrich and summarize"
    ),
    company_id: Optional[str] = typer.Option(
        None,
        "--company-id",
        help="Company ID to enrich and summarize"
    ),
    brevo_api_key: Optional[str] = typer.Option(
        None,
        "--brevo-api-key",
        envvar="BREVO_API_KEY",
        help="Brevo API key for enrichment (or set BREVO_API_KEY env var)"
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output file path (JSON format). If not specified, prints to stdout"
    ),
    markdown_output: Optional[Path] = typer.Option(
        None,
        "--markdown", "-m",
        help="Output summary as markdown file"
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        envvar="ANTHROPIC_API_KEY",
        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)"
    ),
    model: str = typer.Option(
        "claude-sonnet-4-20250514",
        "--model",
        help="Claude model to use"
    ),
    focus_areas: Optional[str] = typer.Option(
        None,
        "--focus",
        help="Comma-separated list of focus areas"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose logging"
    ),
    pretty: bool = typer.Option(
        True,
        "--pretty/--compact",
        help="Pretty-print JSON output"
    ),
    no_cache: bool = typer.Option(
        False,
        "--no-cache",
        help="Disable caching (generate fresh summary)"
    ),
    force_refresh: bool = typer.Option(
        False,
        "--force-refresh",
        help="Force regeneration even if cache is fresh"
    ),
    cache_ttl: int = typer.Option(
        24,
        "--cache-ttl",
        help="Cache TTL in hours (default: 24)"
    ),
    prompt_file: Optional[Path] = typer.Option(
        None,
        "--prompt-file", "--prompt",
        help="Path to custom prompt template file (Markdown format)"
    )
):
    """
    Generate AI-powered deal summary from enriched CRM data.

    Can work in two modes:
    1. From enriched file: Pass a JSON file from brevo-enrich
    2. Direct enrichment: Pass --deal-id, --contact-id, or --company-id

    Examples:

        # From enriched file
        $ deal-summarize enriched_deal.json -o summary.json

        # Direct from deal ID (enriches + summarizes)
        $ deal-summarize --deal-id 690daec017db693613964d23 -o summary.json

        # From contact email
        $ deal-summarize --contact-email user@example.com -m report.md

        # Use specific model
        $ deal-summarize --deal-id 123 --model claude-opus-4-20250514

        # Focus on specific areas
        $ deal-summarize --deal-id 123 --focus "risks,opportunities"
    """
    setup_logging(verbose)

    try:
        # Validate API key
        if not api_key:
            console.print("[red]Error: ANTHROPIC_API_KEY not configured[/red]")
            console.print("\nPlease set your API key:")
            console.print("  export ANTHROPIC_API_KEY='your-api-key'")
            console.print("Or use: --api-key YOUR_KEY")
            raise typer.Exit(1)

        # Determine input mode: file or entity enrichment
        entity_modes = [deal_id, contact_id, contact_email, company_id]
        entity_count = sum(1 for e in entity_modes if e is not None)

        if input_file is None and entity_count == 0:
            console.print("[red]Error: Must provide either input file or entity ID[/red]")
            console.print("\nUsage:")
            console.print("  From file: deal-summarize enriched.json")
            console.print("  From entity: deal-summarize --deal-id 123")
            raise typer.Exit(1)

        if input_file and entity_count > 0:
            console.print("[red]Error: Cannot use both input file and entity ID[/red]")
            console.print("Choose one input method")
            raise typer.Exit(1)

        if entity_count > 1:
            console.print("[red]Error: Specify only one entity ID option[/red]")
            raise typer.Exit(1)

        # Mode 1: Load from file
        if input_file:
            console.print(f"\n[cyan]Loading enriched data from:[/cyan] {input_file}")
            with open(input_file, 'r') as f:
                enriched_data = json.load(f)

        # Mode 2: Enrich entity directly
        else:
            if not SCRIPT1_AVAILABLE:
                console.print("[red]Error: Script 1 (brevo_data_gatherer) not installed[/red]")
                console.print("\nTo use direct enrichment, install Script 1:")
                console.print("  cd brevo_data_gatherer && pip install -e .")
                raise typer.Exit(1)

            if not brevo_api_key:
                console.print("[red]Error: BREVO_API_KEY not configured[/red]")
                console.print("\nFor enrichment, set your Brevo API key:")
                console.print("  export BREVO_API_KEY='your-brevo-key'")
                console.print("Or use: --brevo-api-key YOUR_KEY")
                raise typer.Exit(1)

            # Determine entity type and identifier
            if deal_id:
                entity_type = "deal"
                entity_id = deal_id
            elif contact_id:
                entity_type = "contact"
                entity_id = contact_id
            elif contact_email:
                entity_type = "contact"
                entity_id = contact_email
            elif company_id:
                entity_type = "company"
                entity_id = company_id

            console.print(f"\n[cyan]Enriching {entity_type}:[/cyan] {entity_id}")
            console.print("[dim]Using Script 1 enrichment with caching...[/dim]")

            # Initialize Script 1 components
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                progress.add_task("Initializing enrichment...", total=None)

                # Load config
                config = load_config()

                # Initialize cache for Script 1
                cache_db_path = config.cache_dir / "cache.db"
                cache_manager = CacheManager(cache_db_path)

                # Initialize Brevo client
                brevo_client = BrevoClient(
                    api_key=brevo_api_key,
                    base_url=config.brevo.base_url,
                    cache_manager=cache_manager
                )

                # Initialize conversations client if cookie configured
                conversations_client = None
                if config.conversations.enabled and config.conversations.cookie_string:
                    conversations_client = ConversationsClient(
                        cookie_string=config.conversations.cookie_string,
                        backend_url=config.conversations.backend_url,
                        cache_manager=cache_manager
                    )

                # Initialize enricher
                enricher = DataEnricher(
                    brevo_client,
                    None,  # linkedin_client
                    None,  # web_client
                    conversations_client,
                    cache_manager
                )

                progress.add_task(f"Enriching {entity_type} data...", total=None)

                # Perform enrichment
                enriched_result = enricher.enrich(
                    entity_identifier=entity_id,
                    entity_type=entity_type
                )

                # Convert EnrichedData to dict (Pydantic v2)
                try:
                    enriched_data = enriched_result.model_dump(mode='json')
                except AttributeError:
                    # Fallback for Pydantic v1
                    enriched_data = json.loads(enriched_result.json())

            # Show enrichment stats
            stats = enriched_data.get("stats", {})
            console.print(f"[green]✓ Enrichment complete[/green]")
            if verbose:
                console.print(f"[dim]  API calls: {stats.get('api_calls_made', 0)}, " +
                            f"Cache hits: {stats.get('cache_hits', 0)}[/dim]")

        # Parse focus areas
        focus_list = None
        if focus_areas:
            focus_list = [area.strip() for area in focus_areas.split(',')]

        # Initialize cache if enabled
        cache = None
        if not no_cache:
            cache_file = DEFAULT_CACHE_DIR / "summaries.db"
            cache = SummaryCache(cache_file, ttl_hours=cache_ttl)
            if verbose:
                console.print(f"[dim]Cache enabled: {cache_file} (TTL: {cache_ttl}h)[/dim]")

        # Load prompt template if custom prompt file specified
        prompt_template = None
        if prompt_file:
            try:
                if verbose:
                    console.print(f"[dim]Loading prompt from: {prompt_file}[/dim]")
                prompt_template = PromptLoader.load_prompt_file(prompt_file)
                console.print(f"[green]✓[/green] Loaded custom prompt from {prompt_file}")
            except Exception as e:
                console.print(f"[red]Error loading prompt file: {e}[/red]")
                raise typer.Exit(1)

        # Initialize components
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            progress.add_task("Initializing AI client...", total=None)
            ai_client = AIClient(api_key=api_key, model=model)

            progress.add_task("Checking cache and analyzing data...", total=None)
            summarizer = DealSummarizer(ai_client, cache=cache, prompt_template=prompt_template)

            if cache and not force_refresh:
                progress.add_task("Checking for cached summary...", total=None)

            progress.add_task("Generating summary with Claude AI...", total=None)
            summary = summarizer.summarize(
                enriched_data,
                focus_areas=focus_list,
                force_refresh=force_refresh
            )

        # Display summary
        if summary.is_cached:
            console.print("\n[green]✓ Using cached summary![/green] [dim](data unchanged, cache fresh)[/dim]\n")
        elif summary.previous_summary_date:
            console.print("\n[green]✓ Summary updated![/green] [dim](detected changes since last summary)[/dim]\n")
        else:
            console.print("\n[green]✓ Summary generated successfully![/green]\n")

        # Show summary panel
        summary_info = [
            f"[cyan]Deal:[/cyan] {summary.deal_name}",
            f"[cyan]Company:[/cyan] {summary.company_name or 'N/A'}",
            f"[cyan]Stakeholders:[/cyan] {len(summary.stakeholders)}",
            f"[cyan]Opportunities:[/cyan] {len(summary.opportunities)}",
            f"[cyan]Risks:[/cyan] {len(summary.risks)}",
            f"[cyan]Confidence:[/cyan] {summary.confidence_score or 'N/A'}"
        ]

        # Add cache status
        if summary.is_cached:
            summary_info.append(f"[yellow]Status:[/yellow] Cached")
        elif summary.previous_summary_date:
            summary_info.append(f"[yellow]Status:[/yellow] Updated from {summary.previous_summary_date[:10]}")
        else:
            summary_info.append(f"[yellow]Status:[/yellow] New")

        console.print(Panel(
            "\n".join(summary_info),
            title="[bold]Summary Overview[/bold]",
            border_style="green"
        ))

        # Display change analysis if available
        if summary.changes_since_last_summary and not summary.is_cached:
            console.print("\n[bold]What Changed Since Last Summary:[/bold]")
            console.print(Panel(
                summary.changes_since_last_summary,
                border_style="yellow",
                title="[bold yellow]Change Analysis[/bold yellow]"
            ))

        # Display full markdown summary
        console.print("\n[bold]Deal Summary:[/bold]")
        from rich.markdown import Markdown
        md = Markdown(summary.executive_summary)
        console.print(md)

        # Output to file if specified
        if output:
            output_data = summary.dict()
            with open(output, 'w') as f:
                if pretty:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(output_data, f, ensure_ascii=False)
            console.print(f"\n[green]✓ JSON output written to:[/green] {output}")

        # Output markdown if specified
        if markdown_output:
            markdown_content = _generate_markdown(summary)
            with open(markdown_output, 'w') as f:
                f.write(markdown_content)
            console.print(f"[green]✓ Markdown report written to:[/green] {markdown_output}")

    except FileNotFoundError:
        console.print(f"[red]Error: Input file not found: {input_file}[/red]")
        raise typer.Exit(1)
    except json.JSONDecodeError:
        console.print(f"[red]Error: Invalid JSON in input file: {input_file}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


def _generate_markdown(summary: DealSummary) -> str:
    """Generate markdown report from summary."""
    lines = []

    lines.append(f"# Deal Summary: {summary.deal_name}\n")
    lines.append(f"**Generated:** {summary.generated_at}\n")

    if summary.company_name:
        lines.append(f"**Company:** {summary.company_name}\n")

    lines.append("\n## Executive Summary\n")
    lines.append(f"{summary.executive_summary}\n")

    lines.append("\n## Current Status\n")
    lines.append(f"{summary.current_status}\n")

    if summary.stakeholders:
        lines.append("\n## Stakeholders\n")
        for stakeholder in summary.stakeholders:
            lines.append(f"- **{stakeholder.name}**")
            if stakeholder.role:
                lines.append(f" - {stakeholder.role}")
            if stakeholder.company:
                lines.append(f" ({stakeholder.company})")
            if stakeholder.engagement_level:
                lines.append(f" - Engagement: {stakeholder.engagement_level}")
            lines.append("\n")

    lines.append("\n## Deal Context\n")
    lines.append(f"{summary.deal_context}\n")

    if summary.opportunities:
        lines.append("\n## Opportunities\n")
        for opp in summary.opportunities:
            lines.append(f"- **{opp.description}** ({opp.importance} importance)\n")
            lines.append(f"  - Source: {opp.source}\n")

    if summary.risks:
        lines.append("\n## Risks & Concerns\n")
        for risk in summary.risks:
            lines.append(f"- **{risk.description}** ({risk.importance} importance)\n")
            lines.append(f"  - Source: {risk.source}\n")

    if summary.requirements:
        lines.append("\n## Requirements\n")
        for req in summary.requirements:
            lines.append(f"- **{req.description}**\n")

    if summary.recent_interactions:
        lines.append("\n## Recent Interactions\n")
        for interaction in summary.recent_interactions:
            lines.append(f"- **{interaction.date}** ({interaction.type}): {interaction.summary}\n")

    lines.append("\n## Next Steps Context\n")
    lines.append(f"{summary.next_steps_context}\n")

    # Add change analysis if available
    if summary.changes_since_last_summary:
        lines.append("\n## Changes Since Last Summary\n")
        lines.append(f"{summary.changes_since_last_summary}\n")

    return "\n".join(lines)


@app.command()
def cache_info():
    """
    Display cache statistics.

    Shows information about cached summaries including count, size, and freshness.
    """
    cache_file = DEFAULT_CACHE_DIR / "summaries.db"

    if not cache_file.exists():
        console.print("[yellow]No cache found[/yellow]")
        console.print(f"\nCache will be created at: {cache_file}")
        return

    cache = SummaryCache(cache_file)
    stats = cache.get_statistics()

    console.print("\n[bold cyan]Summary Cache Statistics[/bold cyan]\n")

    info = [
        f"[cyan]Total Summaries:[/cyan] {stats['total_entries']}",
        f"[cyan]Fresh Summaries:[/cyan] {stats['fresh_entries']} (< {stats['ttl_hours']}h old)",
        f"[cyan]Stale Summaries:[/cyan] {stats['stale_entries']} (> {stats['ttl_hours']}h old)",
        f"[cyan]Total Size:[/cyan] {stats['total_size_mb']} MB",
        f"[cyan]Cache Location:[/cyan] {cache_file}"
    ]

    console.print(Panel(
        "\n".join(info),
        title="[bold]Cache Info[/bold]",
        border_style="cyan"
    ))


@app.command()
def cache_clear(
    all: bool = typer.Option(
        False,
        "--all",
        help="Clear all cache entries (including fresh ones)"
    )
):
    """
    Clear cache entries.

    By default, only clears stale entries. Use --all to clear everything.
    """
    cache_file = DEFAULT_CACHE_DIR / "summaries.db"

    if not cache_file.exists():
        console.print("[yellow]No cache found[/yellow]")
        return

    cache = SummaryCache(cache_file)

    if all:
        cache.clear_cache()
        console.print("[green]✓ All cache cleared[/green]")
    else:
        # Clear only stale entries
        stats_before = cache.get_statistics()
        cache.clear_cache()
        stats_after = cache.get_statistics()

        cleared = stats_before['total_entries'] - stats_after['total_entries']
        console.print(f"[green]✓ Cleared {cleared} stale cache entries[/green]")


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
