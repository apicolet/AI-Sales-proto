"""
CLI for sales engagement action recommendations.
"""
import sys
import typer
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
import logging

# Load environment variables from multiple locations
from sales_engagement_action.config import load_config, load_env_from_multiple_locations, DEFAULT_CACHE_DIR, DEFAULT_COMPANY_CONTEXT
load_env_from_multiple_locations()
from sales_engagement_action.cache.manager import RecommendationCache
from sales_engagement_action.core.recommender import ActionRecommender
from sales_engagement_action.core.feedback_processor import FeedbackProcessor
from sales_engagement_action.models.schemas import FeedbackInput
from sales_engagement_action.utils.context_loader import CompanyContextLoader

app = typer.Typer(help="Sales engagement action recommendations with AI")
console = Console()


@app.command()
def recommend(
    deal_id: str = typer.Argument(..., help="Deal ID to analyze"),
    campaign_context: str = typer.Option(None, "--campaign-context", "-c", help="Campaign context"),
    output: Path = typer.Option(None, "--output", "-o", help="Output JSON file"),
    markdown: Path = typer.Option(None, "--markdown", "-m", help="Output Markdown file"),
    prompt_file: Path = typer.Option(None, "--prompt-file", "--prompt", help="Custom prompt template"),
    force_refresh: bool = typer.Option(False, "--force-refresh", help="Force regeneration"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging")
):
    """Generate action recommendations for a deal."""
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        # Load config
        config = load_config()

        # Initialize cache
        cache_file = DEFAULT_CACHE_DIR / "recommendation_cache.db"
        cache = RecommendationCache(cache_file, ttl_minutes=config.cache_ttl.recommendations)

        # Load custom prompt if provided
        prompt_template = None
        if prompt_file:
            if verbose:
                console.print(f"[dim]Loading prompt from: {prompt_file}[/dim]")
            from sales_engagement_action.utils.prompt_loader import PromptLoader
            prompt_template = PromptLoader.load_prompt_file(prompt_file)
            console.print(f"[green]✓[/green] Loaded custom prompt from {prompt_file}")

        # Initialize recommender
        recommender = ActionRecommender(
            anthropic_api_key=config.anthropic_api_key,
            brevo_api_key=config.brevo_api_key,
            cache=cache,
            prompt_template=prompt_template
        )

        console.print(f"\n[bold]Generating recommendations for deal {deal_id}[/bold]")

        # Generate recommendations
        result = recommender.recommend(
            deal_id=deal_id,
            campaign_context=campaign_context,
            force_refresh=force_refresh
        )

        # Display summary
        status = "✓ Using cached recommendation" if result.is_cached else "✓ Generated new recommendation"
        console.print(f"\n{status}\n")

        # Display overview
        table = Table(title="Recommendation Overview")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Deal", result.deal_name)
        table.add_row("Contact", result.contact_name or "N/A")
        table.add_row("Engagement Level", result.analysis.engagement_level)
        table.add_row("Deal Stage", result.analysis.deal_stage or "N/A")
        table.add_row("P0 Actions", str(len(result.p0_actions)))
        table.add_row("P1 Actions", str(len(result.p1_actions)))
        table.add_row("P2 Actions", str(len(result.p2_actions)))
        
        console.print(table)

        # Display recommendations (markdown)
        console.print("\n[bold]Recommended Actions:[/bold]\n")
        md = Markdown(result.overall_strategy)
        console.print(md)

        # Save outputs if requested
        if output:
            import json
            output.write_text(json.dumps(result.model_dump(mode='json'), indent=2))
            console.print(f"\n[green]✓[/green] Saved JSON to {output}")

        if markdown:
            markdown.write_text(result.overall_strategy)
            console.print(f"[green]✓[/green] Saved Markdown to {markdown}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@app.command()
def feedback(
    recommendation_id: str = typer.Argument(..., help="Recommendation ID"),
    feedback_type: str = typer.Option(..., "--type", "-t", help="positive/negative/neutral"),
    text: str = typer.Option(..., "--text", help="Feedback description"),
    worked: str = typer.Option(None, "--worked", help="What worked well"),
    didnt_work: str = typer.Option(None, "--didnt-work", help="What didn't work"),
    improvement: str = typer.Option(None, "--improvement", help="Suggested improvement"),
    deal_id: str = typer.Option(None, "--deal-id", help="Deal ID"),
    priority: str = typer.Option("P0", "--priority", help="Action priority"),
    channel: str = typer.Option("email", "--channel", help="Action channel"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging")
):
    """Provide feedback on a recommendation."""

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        # Initialize cache
        cache_file = DEFAULT_CACHE_DIR / "recommendation_cache.db"
        cache = RecommendationCache(cache_file)

        # Initialize feedback processor
        processor = FeedbackProcessor(
            cache=cache,
            context_file=DEFAULT_COMPANY_CONTEXT
        )

        # Create feedback input
        feedback_input = FeedbackInput(
            recommendation_id=recommendation_id,
            action_priority=priority,
            action_channel=channel,
            feedback_type=feedback_type,
            feedback_text=text,
            what_worked=worked,
            what_didnt_work=didnt_work,
            suggested_improvement=improvement,
            deal_id=deal_id
        )

        console.print(f"\n[bold]Processing feedback for {recommendation_id}[/bold]\n")

        # Process feedback
        result = processor.process_feedback(feedback_input)

        if result.status == "success":
            console.print("[green]✓ Feedback processed successfully![/green]\n")
            
            panel = Panel.fit(
                f"[bold]Learning Extracted:[/bold]\n{result.learning_extracted}\n\n"
                f"[bold]Added to Section:[/bold] {result.added_to_section}\n"
                f"[bold]New Version:[/bold] {result.new_version}\n"
                f"[bold]Will Apply To:[/bold] {result.will_apply_to}",
                title="Feedback Summary",
                border_style="green"
            )
            console.print(panel)
        else:
            console.print(f"[red]✗ Error:[/red] {result.error_message}")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@app.command("cache-info")
def cache_info():
    """Display cache statistics."""
    try:
        cache_file = DEFAULT_CACHE_DIR / "recommendation_cache.db"
        cache = RecommendationCache(cache_file)
        
        stats = cache.get_statistics()
        
        table = Table(title="Cache Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Recommendations", str(stats["total_recommendations"]))
        table.add_row("Fresh (Valid)", str(stats["fresh_recommendations"]))
        table.add_row("Expired (Stale)", str(stats["expired_recommendations"]))
        table.add_row("Total Feedback", str(stats["total_feedback"]))
        table.add_row("Context Updates", str(stats["total_context_updates"]))
        table.add_row("TTL (minutes)", str(stats["ttl_minutes"]))
        
        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@app.command("cache-clear")
def cache_clear(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation")
):
    """Clear recommendation cache."""
    if not confirm:
        confirmed = typer.confirm("Are you sure you want to clear all cached recommendations?")
        if not confirmed:
            console.print("Cancelled")
            return

    try:
        cache_file = DEFAULT_CACHE_DIR / "recommendation_cache.db"
        cache = RecommendationCache(cache_file)
        cache.clear_cache()
        
        console.print("[green]✓[/green] Cache cleared successfully")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@app.command("context-init")
def context_init():
    """Initialize company context template."""
    try:
        CompanyContextLoader.create_default_template(DEFAULT_COMPANY_CONTEXT)
        console.print(f"[green]✓[/green] Created default company context at:")
        console.print(f"  {DEFAULT_COMPANY_CONTEXT}")
        console.print("\nEdit this file to customize your company's sales context.")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def main():
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
