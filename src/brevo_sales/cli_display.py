"""
CLI display formatters for structured recommendations.

Provides multiple output formats:
- Card: Rich terminal display with colors and formatting
- JSON: Machine-readable JSON output
- Markdown: Human-readable text format
"""
import json
from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.syntax import Syntax

from brevo_sales.recommendations.action_models import (
    ActionRecommendations,
    ExecutableAction,
    EmailAction,
    PhoneAction,
    LinkedInAction,
    WhatsAppAction,
)

console = Console()


def format_card(recommendations: ActionRecommendations, show_validation: bool = True) -> None:
    """
    Display recommendations in rich card format.

    Args:
        recommendations: Structured recommendations to display
        show_validation: Whether to show validation warnings
    """
    # Header
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]{recommendations.deal_name}[/bold cyan]\n"
        f"Deal ID: {recommendations.deal_id}",
        title="📊 Sales Action Recommendations",
        border_style="cyan"
    ))
    console.print()

    # Contact Info
    if recommendations.contact_name or recommendations.contact_email:
        contact_info = []
        if recommendations.contact_name:
            contact_info.append(f"👤 {recommendations.contact_name}")
        if recommendations.contact_email:
            contact_info.append(f"✉️  {recommendations.contact_email}")
        console.print(" • ".join(contact_info))
        console.print()

    # Executive Summary
    console.print(Panel(
        recommendations.executive_summary,
        title="[bold]Executive Summary[/bold]",
        border_style="blue"
    ))
    console.print()

    # Key Insights
    if recommendations.key_insights:
        console.print("[bold]🔍 Key Insights:[/bold]")
        for insight in recommendations.key_insights:
            console.print(f"  • {insight}")
        console.print()

    # Actions by Priority
    _display_priority_actions("🔴 P0 - URGENT (Do Immediately)", recommendations.p0_actions, "red")
    _display_priority_actions("🟡 P1 - Important (Do This Week)", recommendations.p1_actions, "yellow")
    _display_priority_actions("🟢 P2 - Nice-to-Have (Do When Possible)", recommendations.p2_actions, "green")

    # Overall Strategy
    console.print(Panel(
        recommendations.overall_strategy,
        title="[bold]🎯 Overall Strategy[/bold]",
        border_style="magenta"
    ))
    console.print()

    # Metadata
    console.print(f"[dim]Generated: {recommendations.generated_at}[/dim]")
    console.print(f"[dim]Data Version: {recommendations.data_version}[/dim]")
    if recommendations.is_cached:
        console.print("[dim]⚡ From cache[/dim]")
    console.print()


def _display_priority_actions(title: str, actions: List[ExecutableAction], color: str) -> None:
    """Display actions for a specific priority level."""
    if not actions:
        return

    console.print(f"[bold {color}]{title}[/bold {color}]")
    console.print()

    for i, action in enumerate(actions, 1):
        # Action header with type
        action_type = action.action.type.upper()
        action_icon = {
            "email": "📧",
            "phone": "📞",
            "linkedin": "💼",
            "whatsapp": "💬"
        }.get(action.action.type, "📋")

        console.print(f"[bold]{action_icon} Action {i}: {action_type}[/bold]")

        # Action details based on type
        if isinstance(action.action, EmailAction):
            _display_email_action(action.action)
        elif isinstance(action.action, PhoneAction):
            _display_phone_action(action.action)
        elif isinstance(action.action, LinkedInAction):
            _display_linkedin_action(action.action)
        elif isinstance(action.action, WhatsAppAction):
            _display_whatsapp_action(action.action)

        # Prerequisites
        if action.prerequisites:
            console.print(f"\n[yellow]📋 Prerequisites ({len(action.prerequisites)}):[/yellow]")
            for prereq in action.prerequisites:
                status_icon = {
                    "todo": "⏳",
                    "in_progress": "🔄",
                    "completed": "✅",
                    "blocked": "🚫"
                }.get(prereq.status, "❓")
                blocking = " [red](BLOCKING)[/red]" if prereq.blocking else ""
                console.print(f"  {status_icon} {prereq.task}{blocking}")
                if prereq.assignee:
                    console.print(f"     👤 {prereq.assignee}")

        # Timing & Rationale
        console.print(f"\n⏰ [bold]Timing:[/bold] {action.recommended_timing}")
        console.print(f"💡 [bold]Rationale:[/bold] {action.rationale}")

        # Success Metrics
        if action.success_metrics:
            console.print(f"\n🎯 [bold]Success Metrics:[/bold]")
            for metric in action.success_metrics:
                console.print(f"  • {metric}")

        console.print()
        console.print("─" * 80)
        console.print()


def _display_email_action(action: EmailAction) -> None:
    """Display email action details."""
    console.print(f"  From: {action.from_name} <{action.from_email}>")
    console.print(f"  To: {action.to_name} <{action.to_email}>")
    if action.cc_emails:
        console.print(f"  CC: {', '.join(action.cc_emails)}")
    console.print(f"  Subject: [cyan]{action.subject}[/cyan]")

    # Content preview (first 200 chars)
    content_preview = action.content[:200] + "..." if len(action.content) > 200 else action.content
    console.print(f"\n  Content Preview:")
    console.print(Panel(content_preview, border_style="dim"))

    if action.attachments:
        console.print(f"  📎 Attachments: {len(action.attachments)}")


def _display_phone_action(action: PhoneAction) -> None:
    """Display phone action details."""
    console.print(f"  Call: {action.to_name} at {action.to_phone}")
    console.print(f"  Objective: {action.objective}")
    console.print(f"  Duration: ~{action.expected_duration_minutes} minutes")

    console.print(f"\n  Talking Points:")
    for i, point in enumerate(action.talking_points, 1):
        console.print(f"    {i}. {point}")


def _display_linkedin_action(action: LinkedInAction) -> None:
    """Display LinkedIn action details."""
    console.print(f"  To: {action.recipient_name}")
    console.print(f"  Profile: {action.recipient_linkedin_url}")
    console.print(f"  Action: {action.action_type.replace('_', ' ').title()}")

    if action.subject:
        console.print(f"  Subject: {action.subject}")

    # Message preview
    message_preview = action.message[:200] + "..." if len(action.message) > 200 else action.message
    console.print(f"\n  Message Preview:")
    console.print(Panel(message_preview, border_style="dim"))


def _display_whatsapp_action(action: WhatsAppAction) -> None:
    """Display WhatsApp action details."""
    console.print(f"  To: {action.to_name} at {action.to_phone}")

    # Message preview
    message_preview = action.message[:200] + "..." if len(action.message) > 200 else action.message
    console.print(f"\n  Message Preview:")
    console.print(Panel(message_preview, border_style="dim"))

    if action.media_url:
        console.print(f"  📎 Media: {action.media_url}")


def format_json(recommendations: ActionRecommendations, indent: int = 2) -> str:
    """
    Format recommendations as JSON.

    Args:
        recommendations: Structured recommendations
        indent: JSON indentation level

    Returns:
        JSON string
    """
    data = recommendations.model_dump(mode='json')
    return json.dumps(data, indent=indent, ensure_ascii=False)


def format_markdown(recommendations: ActionRecommendations) -> str:
    """
    Format recommendations as markdown.

    Args:
        recommendations: Structured recommendations

    Returns:
        Markdown string
    """
    lines = []

    # Header
    lines.append(f"# Sales Action Recommendations")
    lines.append(f"## {recommendations.deal_name}")
    lines.append(f"**Deal ID:** {recommendations.deal_id}")
    lines.append("")

    # Contact
    if recommendations.contact_name or recommendations.contact_email:
        lines.append(f"**Primary Contact:**")
        if recommendations.contact_name:
            lines.append(f"- Name: {recommendations.contact_name}")
        if recommendations.contact_email:
            lines.append(f"- Email: {recommendations.contact_email}")
        lines.append("")

    # Executive Summary
    lines.append(f"## Executive Summary")
    lines.append(f"{recommendations.executive_summary}")
    lines.append("")

    # Key Insights
    if recommendations.key_insights:
        lines.append(f"## Key Insights")
        for insight in recommendations.key_insights:
            lines.append(f"- {insight}")
        lines.append("")

    # Actions by Priority
    if recommendations.p0_actions:
        lines.append(f"## 🔴 P0 Actions (Urgent - Do Immediately)")
        lines.append("")
        for i, action in enumerate(recommendations.p0_actions, 1):
            lines.extend(_format_action_markdown(i, action))

    if recommendations.p1_actions:
        lines.append(f"## 🟡 P1 Actions (Important - Do This Week)")
        lines.append("")
        for i, action in enumerate(recommendations.p1_actions, 1):
            lines.extend(_format_action_markdown(i, action))

    if recommendations.p2_actions:
        lines.append(f"## 🟢 P2 Actions (Nice-to-Have - Do When Possible)")
        lines.append("")
        for i, action in enumerate(recommendations.p2_actions, 1):
            lines.extend(_format_action_markdown(i, action))

    # Overall Strategy
    lines.append(f"## Overall Strategy")
    lines.append(f"{recommendations.overall_strategy}")
    lines.append("")

    # Metadata
    lines.append(f"---")
    lines.append(f"*Generated: {recommendations.generated_at}*")
    lines.append(f"*Data Version: {recommendations.data_version}*")
    if recommendations.is_cached:
        lines.append(f"*Source: Cache*")

    return "\n".join(lines)


def _format_action_markdown(index: int, action: ExecutableAction) -> List[str]:
    """Format a single action as markdown."""
    lines = []

    action_icon = {
        "email": "📧",
        "phone": "📞",
        "linkedin": "💼",
        "whatsapp": "💬"
    }.get(action.action.type, "📋")

    lines.append(f"### {action_icon} Action {index}: {action.action.type.upper()}")
    lines.append("")

    # Action-specific details
    if isinstance(action.action, EmailAction):
        lines.append(f"**From:** {action.action.from_name} <{action.action.from_email}>")
        lines.append(f"**To:** {action.action.to_name} <{action.action.to_email}>")
        if action.action.cc_emails:
            lines.append(f"**CC:** {', '.join(action.action.cc_emails)}")
        lines.append(f"**Subject:** {action.action.subject}")
        lines.append("")
        lines.append(f"**Content:**")
        lines.append("```")
        lines.append(action.action.content)
        lines.append("```")
        if action.action.attachments:
            lines.append(f"**Attachments:** {len(action.action.attachments)}")

    elif isinstance(action.action, PhoneAction):
        lines.append(f"**Call:** {action.action.to_name} at {action.action.to_phone}")
        lines.append(f"**Objective:** {action.action.objective}")
        lines.append(f"**Duration:** ~{action.action.expected_duration_minutes} minutes")
        lines.append("")
        lines.append(f"**Talking Points:**")
        for i, point in enumerate(action.action.talking_points, 1):
            lines.append(f"{i}. {point}")

    elif isinstance(action.action, LinkedInAction):
        lines.append(f"**To:** {action.action.recipient_name}")
        lines.append(f"**Profile:** {action.action.recipient_linkedin_url}")
        lines.append(f"**Action Type:** {action.action.action_type.replace('_', ' ').title()}")
        if action.action.subject:
            lines.append(f"**Subject:** {action.action.subject}")
        lines.append("")
        lines.append(f"**Message:**")
        lines.append("```")
        lines.append(action.action.message)
        lines.append("```")

    elif isinstance(action.action, WhatsAppAction):
        lines.append(f"**To:** {action.action.to_name} at {action.action.to_phone}")
        lines.append("")
        lines.append(f"**Message:**")
        lines.append("```")
        lines.append(action.action.message)
        lines.append("```")
        if action.action.media_url:
            lines.append(f"**Media:** {action.action.media_url}")

    lines.append("")

    # Prerequisites
    if action.prerequisites:
        lines.append(f"**Prerequisites ({len(action.prerequisites)}):**")
        for prereq in action.prerequisites:
            status_text = prereq.status.upper()
            blocking_text = " (BLOCKING)" if prereq.blocking else ""
            lines.append(f"- [{status_text}] {prereq.task}{blocking_text}")
            if prereq.assignee:
                lines.append(f"  - Assignee: {prereq.assignee}")
        lines.append("")

    # Context & Rationale
    lines.append(f"**Timing:** {action.recommended_timing}")
    lines.append(f"**Rationale:** {action.rationale}")
    lines.append("")

    # Success Metrics
    if action.success_metrics:
        lines.append(f"**Success Metrics:**")
        for metric in action.success_metrics:
            lines.append(f"- {metric}")
        lines.append("")

    return lines


def display_validation_warnings(warnings: List[str]) -> None:
    """
    Display validation warnings.

    Args:
        warnings: List of warning messages
    """
    if not warnings:
        console.print("[green]✓ All actions passed validation checks[/green]")
        return

    console.print(f"\n[yellow]⚠️  Validation Warnings ({len(warnings)}):[/yellow]")
    for warning in warnings:
        console.print(f"  • {warning}")
    console.print()
