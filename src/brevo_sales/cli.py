"""
Unified CLI for Brevo Sales AI Agent.

Combines enrichment, summarization, and recommendation commands into one interface.
"""
import sys
import json
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.json import JSON
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown

# Load environment variables from multiple locations
from brevo_sales.config import load_env_from_multiple_locations, load_config, DEFAULT_CACHE_DIR, DEFAULT_COMPANY_CONTEXT
load_env_from_multiple_locations()

app = typer.Typer(
    help="Brevo Sales AI Agent - CRM enrichment, deal summarization, and action recommendations",
    add_completion=False
)
console = Console()


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def _create_enricher(config, no_linkedin: bool = False, no_web_search: bool = False):
    """
    Create and configure a DataEnricher with all necessary clients.

    This is a shared helper to avoid code duplication between enrich and summarize commands.

    Args:
        config: Configuration object
        no_linkedin: Disable LinkedIn enrichment
        no_web_search: Disable web search enrichment

    Returns:
        Configured DataEnricher instance
    """
    from brevo_sales.enrichment.enricher import DataEnricher
    from brevo_sales.enrichment.brevo_client import BrevoClient
    from brevo_sales.enrichment.linkedin_client import LinkedInClient
    from brevo_sales.enrichment.web_client import WebSearchClient
    from brevo_sales.cache.manager import CacheManager

    # Initialize cache
    cache_manager = CacheManager(config.cache_dir / "enrichment.db")

    # Initialize Brevo client
    brevo_client = BrevoClient(
        api_key=config.brevo.api_key,
        base_url=config.brevo.base_url,
        cache_manager=cache_manager
    )

    # Initialize optional clients
    linkedin_client = None
    if not no_linkedin and config.linkedin.pipedream_workflow_url:
        linkedin_client = LinkedInClient(
            provider=config.linkedin.provider,
            cache_manager=cache_manager,
            pipedream_workflow_url=config.linkedin.pipedream_workflow_url
        )

    web_client = None
    if not no_web_search and config.web_search.api_key:
        web_client = WebSearchClient(
            provider=config.web_search.provider,
            cache_manager=cache_manager,
            api_key=config.web_search.api_key
        )

    # Create and return enricher
    return DataEnricher(
        brevo_client=brevo_client,
        linkedin_client=linkedin_client,
        web_client=web_client,
        cache_manager=cache_manager
    )


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
    output_file: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output file path for enriched data (JSON format)"
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
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose logging"
    ),
):
    """
    Enrich Brevo CRM data with multiple sources.

    Fetches and combines data from:
    - Brevo API (contacts, deals, companies, notes, tasks)
    - LinkedIn profiles (optional)
    - Web search intelligence (optional)

    Example:
        brevo-sales enrich contact@example.com
        brevo-sales enrich 61a5ce58c5d4795761045990 --type deal -o enriched.json
    """
    setup_logging(verbose)

    try:
        # Load configuration
        config = load_config()

        # Create enricher using shared helper
        enricher = _create_enricher(config, no_linkedin, no_web_search)

        # Enrich with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Enriching data...", total=None)
            enriched_data = enricher.enrich(entity_identifier, entity_type)
            progress.update(task, completed=True)

        # Convert to dict for output
        data_dict = enriched_data.dict()

        # Output
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(data_dict, f, indent=2, default=str)
            console.print(f"[green]✓[/green] Enriched data saved to: {output_file}")
        else:
            console.print(JSON(json.dumps(data_dict, default=str)))

        # Print summary
        console.print(f"\n[bold]Enrichment Summary:[/bold]")
        console.print(f"  Entity Type: {enriched_data.primary_type}")
        console.print(f"  API Calls: {enriched_data.metadata.get('api_calls_made', 'N/A')}")
        console.print(f"  Cache Hit Rate: {enriched_data.metadata.get('cache_hit_rate', 0):.0%}")
        console.print(f"  Sources: {', '.join(enriched_data.metadata.get('sources_used', []))}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", style="bold red")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@app.command()
def summarize(
    deal_id: Optional[str] = typer.Argument(
        None,
        help="Deal ID to summarize (or provide --input with enriched data file)"
    ),
    input_file: Optional[Path] = typer.Option(
        None,
        "--input", "-i",
        help="Input file with enriched data (JSON)"
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output file for summary (JSON)"
    ),
    markdown: Optional[Path] = typer.Option(
        None,
        "--markdown", "-m",
        help="Output file for markdown report"
    ),
    model: str = typer.Option(
        "claude-sonnet-4-20250514",
        "--model",
        help="Claude model to use"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose logging"
    ),
):
    """
    Generate AI-powered deal summaries.

    Analyzes enriched CRM data to provide:
    - Executive summary
    - Stakeholder analysis
    - Opportunities and risks
    - Recent interaction timeline
    - Next steps context

    Example:
        brevo-sales summarize 61a5ce58c5d4795761045990
        brevo-sales summarize --input enriched.json -o summary.json -m report.md
    """
    setup_logging(verbose)

    try:
        from brevo_sales.summarization.summarizer import DealSummarizer
        from brevo_sales.summarization.ai_client import AIClient

        # Validate inputs
        if not deal_id and not input_file:
            console.print("[red]Error:[/red] Must provide either deal_id or --input file")
            sys.exit(1)

        # Load configuration
        config = load_config()
        if not config.anthropic_api_key:
            console.print("[red]Error:[/red] ANTHROPIC_API_KEY not found in environment")
            sys.exit(1)

        # Get enriched data
        if input_file:
            with open(input_file) as f:
                enriched_data = json.load(f)
        else:
            # Run enrichment first
            console.print(f"Enriching deal {deal_id} first...")

            # Validate API key
            if not config.brevo.api_key:
                console.print("[red]Error:[/red] BREVO_API_KEY not found in environment")
                sys.exit(1)

            # Create enricher using shared helper
            enricher = _create_enricher(config)

            # Enrich with progress indicator
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Enriching CRM data...", total=None)
                enriched_data_obj = enricher.enrich(deal_id, "deal")
                progress.update(task, completed=True)

            # Convert to dict for summarizer (using mode='json' to handle datetime serialization)
            enriched_data = enriched_data_obj.model_dump(mode='json')

        # Initialize AI client and summarizer
        ai_client = AIClient(api_key=config.anthropic_api_key, model=model)
        summarizer = DealSummarizer(ai_client)

        # Generate summary with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating AI summary...", total=None)
            summary = summarizer.summarize(enriched_data)
            progress.update(task, completed=True)

        # Output JSON
        if output:
            with open(output, 'w') as f:
                json.dump(summary.dict(), f, indent=2, default=str)
            console.print(f"[green]✓[/green] Summary saved to: {output}")

        # Output Markdown
        if markdown:
            with open(markdown, 'w') as f:
                f.write(summary.executive_summary)
            console.print(f"[green]✓[/green] Markdown report saved to: {markdown}")

        # Print to console if no output files
        if not output and not markdown:
            console.print(Markdown(summary.executive_summary))

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", style="bold red")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@app.command()
def recommend(
    deal_id: str = typer.Argument(..., help="Deal ID to analyze"),
    campaign_context: Optional[str] = typer.Option(
        None,
        "--campaign-context", "-c",
        help="Additional campaign context"
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output file for recommendations (JSON)"
    ),
    markdown: Optional[Path] = typer.Option(
        None,
        "--markdown", "-m",
        help="Output file for markdown strategy"
    ),
    force_refresh: bool = typer.Option(
        False,
        "--force-refresh",
        help="Bypass cache and regenerate"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose logging"
    ),
):
    """
    Generate next-best-action recommendations.

    Provides prioritized, channel-specific recommendations:
    - P0 actions (execute today) with full content
    - P1 actions (this week) with strategic outlines
    - P2 actions (next week) with brief outlines

    Example:
        brevo-sales recommend 690daec017db693613964d23
        brevo-sales recommend 690daec017db693613964d23 -c "Q4 product launch" -o results.json
    """
    setup_logging(verbose)

    try:
        from brevo_sales.recommendations.recommender import ActionRecommender

        # Load configuration
        config = load_config()
        if not config.anthropic_api_key:
            console.print("[red]Error:[/red] ANTHROPIC_API_KEY not found in environment")
            sys.exit(1)
        if not config.brevo.api_key:
            console.print("[red]Error:[/red] BREVO_API_KEY not found in environment")
            sys.exit(1)

        # Create recommender
        recommender = ActionRecommender(
            anthropic_api_key=config.anthropic_api_key,
            brevo_api_key=config.brevo.api_key
        )

        # Generate recommendations with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating recommendations...", total=None)
            result = recommender.recommend(
                deal_id=deal_id,
                campaign_context=campaign_context,
                force_refresh=force_refresh
            )
            progress.update(task, completed=True)

        # Output JSON
        if output:
            with open(output, 'w') as f:
                json.dump(result.dict(), f, indent=2, default=str)
            console.print(f"[green]✓[/green] Recommendations saved to: {output}")

        # Output Markdown
        if markdown:
            md_content = result.to_markdown()
            with open(markdown, 'w') as f:
                f.write(md_content)
            console.print(f"[green]✓[/green] Strategy saved to: {markdown}")

        # Print summary to console
        table = Table(title="Recommendation Overview")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Deal", result.deal_name or deal_id)
        table.add_row("Contact", result.primary_contact or "N/A")
        table.add_row("P0 Actions", str(len(result.p0_actions)))
        table.add_row("P1 Actions", str(len(result.p1_actions)))
        table.add_row("P2 Actions", str(len(result.p2_actions)))

        console.print(table)

        if not output and not markdown:
            console.print("\n[dim]Use -o/--output for JSON or -m/--markdown for full report[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", style="bold red")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@app.command()
def feedback(
    recommendation_id: str = typer.Argument(..., help="Recommendation ID"),
    feedback_type: str = typer.Option(..., "--type", "-t", help="positive/negative/neutral"),
    text: str = typer.Option(..., "--text", help="Feedback description"),
    worked: Optional[str] = typer.Option(None, "--worked", help="What worked well"),
    didnt_work: Optional[str] = typer.Option(None, "--didnt-work", help="What didn't work"),
    improvement: Optional[str] = typer.Option(None, "--improvement", help="Suggested improvement"),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose logging"
    ),
):
    """
    Provide feedback on action recommendations.

    Feedback is used to improve future recommendations through
    continuous learning and company context updates.

    Example:
        brevo-sales feedback rec_abc123 -t positive --text "Email worked great"
    """
    setup_logging(verbose)

    try:
        from brevo_sales.recommendations.feedback_processor import FeedbackProcessor
        from brevo_sales.recommendations.models import FeedbackInput
        from brevo_sales.cache.manager import CacheManager

        config = load_config()
        cache = CacheManager(config.cache_dir / "recommendations.db")

        processor = FeedbackProcessor(cache=cache)

        feedback_input = FeedbackInput(
            recommendation_id=recommendation_id,
            feedback_type=feedback_type,
            feedback_text=text,
            what_worked=worked,
            what_didnt_work=didnt_work,
            suggested_improvement=improvement
        )

        result = processor.process_feedback(feedback_input)

        console.print(f"[green]✓[/green] Feedback recorded")
        if result.get("learning_extracted"):
            console.print(f"[blue]Learning:[/blue] {result['learning_extracted']}")
        if result.get("context_updated"):
            console.print(f"[green]✓[/green] Company context updated")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", style="bold red")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@app.command("cache-info")
def cache_info():
    """Display cache statistics for all modules."""
    try:
        config = load_config()
        cache_dir = config.cache_dir

        table = Table(title="Cache Statistics")
        table.add_column("Module", style="cyan")
        table.add_column("Entries", style="green")
        table.add_column("Fresh", style="green")
        table.add_column("Expired", style="yellow")

        # Check each cache database
        from brevo_sales.cache.manager import CacheManager

        modules = ["enrichment", "summarization", "recommendations"]
        for module in modules:
            db_path = cache_dir / f"{module}.db"
            if db_path.exists():
                cache = CacheManager(db_path)
                stats = cache.get_stats()
                table.add_row(
                    module.capitalize(),
                    str(stats.get("total_entries", 0)),
                    str(stats.get("fresh_entries", 0)),
                    str(stats.get("expired_entries", 0))
                )
            else:
                table.add_row(module.capitalize(), "0", "0", "0")

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", style="bold red")
        sys.exit(1)


@app.command("cache-clear")
def cache_clear(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    module: Optional[str] = typer.Option(None, "--module", "-m", help="Specific module: enrichment, summarization, recommendations")
):
    """Clear cache for all modules or a specific module."""
    try:
        config = load_config()
        cache_dir = config.cache_dir

        if module:
            modules_to_clear = [module]
        else:
            modules_to_clear = ["enrichment", "summarization", "recommendations"]

        if not confirm:
            module_list = ", ".join(modules_to_clear)
            if not typer.confirm(f"Clear cache for: {module_list}?"):
                console.print("Cancelled")
                return

        from brevo_sales.cache.manager import CacheManager

        for mod in modules_to_clear:
            db_path = cache_dir / f"{mod}.db"
            if db_path.exists():
                cache = CacheManager(db_path)
                cache.clear_all()
                console.print(f"[green]✓[/green] Cleared {mod} cache")

        console.print("[green]✓[/green] Cache cleared successfully")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", style="bold red")
        sys.exit(1)


@app.command("context-init")
def context_init():
    """Initialize company context template for recommendations."""
    try:
        config = load_config()
        context_file = config.company_context_file

        if context_file.exists():
            if not typer.confirm(f"Context file already exists at {context_file}. Overwrite?"):
                console.print("Cancelled")
                return

        context_file.parent.mkdir(parents=True, exist_ok=True)

        template = """# Company Context - Brevo Sales

Version: 1.0

## Company Overview
[Your company details, value proposition, target market]

## Product/Service Details
[Products and services offered, key features, pricing model]

## Target Audience
[Ideal customer profile, buyer personas, decision makers]

## Communication Guidelines
[Tone, style, best practices for customer communication]

## Email Engagement Learnings
- **YYYY-MM-DD**: [Learning from feedback] _(Context: [action details])_

## Call Strategy Learnings
- **YYYY-MM-DD**: [Learning from feedback] _(Context: [action details])_

## LinkedIn Outreach Learnings
- **YYYY-MM-DD**: [Learning from feedback] _(Context: [action details])_

## WhatsApp Communication Learnings
- **YYYY-MM-DD**: [Learning from feedback] _(Context: [action details])_
"""

        with open(context_file, 'w') as f:
            f.write(template)

        console.print(f"[green]✓[/green] Context template created at: {context_file}")
        console.print("\n[dim]Edit this file to customize your company context.[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", style="bold red")
        sys.exit(1)


@app.command()
def update_cookie(
    curl_command: str = typer.Argument(
        ...,
        help="Full cURL command containing cookie (paste entire command from Chrome DevTools)"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose logging"
    ),
):
    """
    Update BREVO_COOKIE from a cURL command.

    Extracts the cookie from -b or --cookie parameter and updates
    the ~/.ai-sales/.env file. Useful when your Brevo session expires.

    Example:
        brevo-sales update-cookie "curl -b 'session=abc; token=xyz' https://..."
    """
    setup_logging(verbose)

    try:
        import re

        # Extract cookie from cURL command
        # Match -b or --cookie followed by quoted or unquoted value
        pattern = r"(?:-b|--cookie)\s+(?:'([^']*)'|\"([^\"]*)\"|(\S+))"
        match = re.search(pattern, curl_command, re.DOTALL)

        if not match:
            console.print("[red]Error:[/red] Could not find -b or --cookie parameter in cURL command")
            console.print("\n[dim]Expected format:[/dim]")
            console.print("  curl -b 'cookie_string' ...")
            console.print("  curl --cookie 'cookie_string' ...")
            sys.exit(1)

        # Extract cookie value (from whichever group matched)
        cookie_value = match.group(1) or match.group(2) or match.group(3)
        cookie_value = cookie_value.strip()

        if not cookie_value:
            console.print("[red]Error:[/red] Cookie value is empty")
            sys.exit(1)

        # Validate cookie format (should have at least one =)
        if '=' not in cookie_value:
            console.print("[red]Error:[/red] Invalid cookie format (no key=value pairs found)")
            sys.exit(1)

        # Count cookie pairs
        cookie_pairs = [p.strip() for p in cookie_value.split(';') if '=' in p]

        if verbose:
            console.print(f"[dim]Found {len(cookie_pairs)} cookie pairs[/dim]")

        # Update .env file
        env_path = Path.home() / ".ai-sales" / ".env"

        if not env_path.exists():
            console.print(f"[yellow]Warning:[/yellow] {env_path} does not exist, creating it...")
            env_path.parent.mkdir(parents=True, exist_ok=True)
            env_path.write_text("")

        # Read current content
        lines = env_path.read_text().splitlines()

        # Find and update BREVO_COOKIE line
        updated = False
        new_lines = []
        for line in lines:
            if line.startswith("BREVO_COOKIE="):
                new_lines.append(f"BREVO_COOKIE={cookie_value}")
                updated = True
                if verbose:
                    console.print(f"[dim]Updated existing BREVO_COOKIE line[/dim]")
            else:
                new_lines.append(line)

        # If not found, add it after the cookie comment if exists, or at the end
        if not updated:
            # Try to find the cookie comment line
            inserted = False
            for i, line in enumerate(new_lines):
                if "Brevo Cookie" in line and line.startswith("#"):
                    new_lines.insert(i + 1, f"BREVO_COOKIE={cookie_value}")
                    inserted = True
                    if verbose:
                        console.print(f"[dim]Added BREVO_COOKIE after comment line[/dim]")
                    break

            # If still not found, append at the end
            if not inserted:
                if new_lines and new_lines[-1] != "":
                    new_lines.append("")
                new_lines.append("# Brevo Cookie (for Email Conversations - expires periodically)")
                new_lines.append(f"BREVO_COOKIE={cookie_value}")
                if verbose:
                    console.print(f"[dim]Added BREVO_COOKIE at end of file[/dim]")

        # Write back
        env_path.write_text("\n".join(new_lines) + "\n")

        # Success message
        console.print(f"[green]✓[/green] Cookie updated successfully in {env_path}")
        console.print(f"\n[bold]Cookie Summary:[/bold]")
        console.print(f"  Cookie pairs: {len(cookie_pairs)}")

        if cookie_pairs:
            first_cookie = cookie_pairs[0].split('=')[0]
            last_cookie = cookie_pairs[-1].split('=')[0]
            console.print(f"  First cookie: {first_cookie}")
            console.print(f"  Last cookie: {last_cookie}")

        console.print(f"\n[dim]The cookie will be used for Conversations API authentication.[/dim]")
        console.print(f"[dim]You can now run enrichment commands that use the Conversations API.[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", style="bold red")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


def main():
    """Main entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
