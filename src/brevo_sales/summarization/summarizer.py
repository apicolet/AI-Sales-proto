"""
Deal summarization logic using AI.
"""
import json
import logging
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from brevo_sales.summarization.ai_client import AIClient
from brevo_sales.summarization.models import DealSummary
from brevo_sales.summarization.cache import SummaryCache
from brevo_sales.summarization.diff import compute_enriched_data_diff, format_diff_for_ai
from brevo_sales.summarization.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class DealSummarizer:
    """Generates AI-powered deal summaries from enriched data with intelligent caching."""

    def __init__(
        self,
        ai_client: AIClient,
        cache: Optional[SummaryCache] = None,
        prompt_template: Optional[str] = None
    ):
        """
        Initialize summarizer.

        Args:
            ai_client: AI client for Claude API
            cache: Optional cache manager for summary caching
            prompt_template: Optional custom prompt template (loaded from file)
        """
        self.ai_client = ai_client
        self.cache = cache
        self.prompt_template = prompt_template or PromptLoader.load_default_prompt()

    def summarize(
        self,
        enriched_data: Dict[str, Any],
        focus_areas: Optional[list[str]] = None,
        force_refresh: bool = False
    ) -> DealSummary:
        """
        Generate comprehensive deal summary from enriched data with intelligent caching.

        Caching behavior:
        - If data unchanged and cache < 24 hours: return cached summary
        - If data changed or cache stale: generate new summary with change analysis
        - Saves all summaries to cache for future diff computation

        Args:
            enriched_data: Output from Script 1 (brevo_data_gatherer)
            focus_areas: Optional list of areas to focus on
            force_refresh: Force regeneration even if cache is fresh

        Returns:
            DealSummary object
        """
        logger.info("Starting deal summarization")

        # Compute data hash for version tracking
        data_hash = self._compute_data_hash(enriched_data)

        # Check cache if enabled
        previous_summary = None
        previous_enriched = None
        diff = None

        if self.cache and not force_refresh:
            cache_result = self.cache.get_cached_summary(enriched_data, self.prompt_template)

            if cache_result:
                cached_summary, is_fresh, prev_enriched = cache_result

                if is_fresh:
                    # Return cached summary
                    logger.info("Using fresh cached summary")
                    summary = DealSummary(**cached_summary)
                    summary.is_cached = True
                    return summary

                # Cache exists but stale or data changed - prepare diff
                logger.info("Cache found but stale/changed, computing diff")
                previous_summary = cached_summary
                previous_enriched = prev_enriched

                # Compute diff for AI analysis
                if previous_enriched:
                    diff = compute_enriched_data_diff(previous_enriched, enriched_data)
                    logger.info(f"Computed diff: {len(diff.get('summary', []))} changes")

        # Build prompts (including diff if available)
        system_prompt = self._build_system_prompt(with_change_analysis=bool(diff))
        user_prompt = self._build_user_prompt(
            enriched_data,
            focus_areas,
            previous_summary=previous_summary,
            diff=diff
        )

        # Generate summary using Claude (Markdown output)
        response = self.ai_client.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format=None  # No structured output, use Markdown
        )

        # Extract markdown text
        markdown_text = response.get("response", "")

        if not markdown_text:
            logger.warning("Empty response from Claude")
            return self._build_fallback_summary(enriched_data, "Empty response")

        logger.info(f"Successfully generated markdown summary ({len(markdown_text)} chars)")

        # Create summary object with markdown
        summary_data = {
            "deal_name": self._extract_deal_name(enriched_data),
            "deal_id": self._extract_deal_id(enriched_data),
            "company_name": self._extract_company_name(enriched_data),
            "deal_stage": None,
            "deal_value": None,
            "executive_summary": markdown_text,  # Store full markdown
            "stakeholders": [],
            "deal_context": "",
            "opportunities": [],
            "risks": [],
            "requirements": [],
            "recent_interactions": [],
            "current_status": "",
            "next_steps_context": "",
            "generated_at": datetime.now().isoformat(),
            "data_sources": ["Script 1 enriched data"],
            "confidence_score": 1.0,
            "data_version": data_hash,
            "is_cached": False,
            "previous_summary_date": previous_summary.get("generated_at") if previous_summary else None,
            "changes_since_last_summary": None
        }

        summary = DealSummary(**summary_data)

        # Save to cache if enabled
        if self.cache:
            self.cache.save_summary(enriched_data, summary.dict(), self.prompt_template)
            logger.info("Saved summary to cache")

        return summary

    def _compute_data_hash(self, enriched_data: Dict[str, Any]) -> str:
        """Compute hash of enriched data."""
        data_str = json.dumps(enriched_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]

    def _build_system_prompt(self, with_change_analysis: bool = False) -> str:
        """
        Build the system prompt for Claude using the loaded template.

        Args:
            with_change_analysis: Whether to include change analysis capabilities
        """
        # Process template variables
        prompt = PromptLoader.process_template_variables(
            self.prompt_template,
            {"with_change_analysis": with_change_analysis}
        )

        return prompt

    def _build_user_prompt(
        self,
        enriched_data: Dict[str, Any],
        focus_areas: Optional[list[str]] = None,
        previous_summary: Optional[Dict[str, Any]] = None,
        diff: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build the user prompt with enriched data.

        Args:
            enriched_data: Enriched CRM data from Script 1
            focus_areas: Optional focus areas
            previous_summary: Previous summary if this is an update
            diff: Diff between previous and current data

        Returns:
            Formatted prompt string
        """
        # Extract key components
        primary_type = enriched_data.get("primary_type", "unknown")
        primary_record = enriched_data.get("primary_record", {})
        related_entities = enriched_data.get("related_entities", {})
        interaction_history = enriched_data.get("interaction_history", {})

        prompt_parts = []

        # Header
        if previous_summary and diff:
            prompt_parts.append("# CRM Data Analysis Request - UPDATE\n")
            prompt_parts.append("**This is an update to a previous summary. Data has changed or sufficient time has passed.**\n")
        else:
            prompt_parts.append("# CRM Data Analysis Request\n")

        # Include previous summary context if available
        if previous_summary:
            prompt_parts.append("\n## Previous Summary Context\n")
            prompt_parts.append(f"**Generated:** {previous_summary.get('generated_at', 'Unknown')}\n")
            prompt_parts.append(f"**Executive Summary:** {previous_summary.get('executive_summary', 'N/A')}\n")
            if previous_summary.get('current_status'):
                prompt_parts.append(f"**Previous Status:** {previous_summary.get('current_status')}\n")

        # Include diff if available
        if diff:
            prompt_parts.append("\n" + format_diff_for_ai(diff))

        # Focus areas if specified
        if focus_areas:
            prompt_parts.append(f"\n**Focus on these areas:** {', '.join(focus_areas)}\n")

        # Primary entity info
        prompt_parts.append(f"## Primary Entity: {primary_type.title()}\n")
        prompt_parts.append(self._format_primary_entity(primary_type, primary_record))

        # Related entities
        contacts = related_entities.get("contacts", [])
        companies = related_entities.get("companies", [])
        deals = related_entities.get("deals", [])

        if contacts:
            prompt_parts.append(f"\n## Contacts ({len(contacts)})\n")
            for contact in contacts[:5]:  # Limit to first 5
                prompt_parts.append(self._format_contact(contact))

        if companies:
            prompt_parts.append(f"\n## Companies ({len(companies)})\n")
            for company in companies[:3]:  # Limit to first 3
                prompt_parts.append(self._format_company(company))

        if deals and primary_type != "deal":
            prompt_parts.append(f"\n## Deals ({len(deals)})\n")
            for deal in deals[:5]:
                prompt_parts.append(self._format_deal(deal))

        # Interaction history
        notes = interaction_history.get("notes", [])
        tasks = interaction_history.get("tasks", [])

        if notes:
            prompt_parts.append(f"\n## Notes ({len(notes)})\n")
            for note in notes:
                prompt_parts.append(self._format_note(note))

        if tasks:
            prompt_parts.append(f"\n## Tasks ({len(tasks)})\n")
            for task in tasks:
                prompt_parts.append(self._format_task(task))

        # Final instruction
        prompt_parts.append("\n\n---\n")
        prompt_parts.append("**Please analyze this CRM data and generate a comprehensive deal summary in Markdown format following the specified structure.**")

        return "\n".join(prompt_parts)

    def _format_primary_entity(self, entity_type: str, record: Dict[str, Any]) -> str:
        """Format primary entity information."""
        if entity_type == "deal":
            return self._format_deal(record)
        elif entity_type == "contact":
            return self._format_contact(record)
        elif entity_type == "company":
            return self._format_company(record)
        return str(record)

    def _format_contact(self, contact: Dict[str, Any]) -> str:
        """Format contact information."""
        lines = []
        lines.append(f"**Contact:** {contact.get('email', 'N/A')}")

        attrs = contact.get('attributes', {})
        if attrs.get('PRENOM') or attrs.get('NOM'):
            name = f"{attrs.get('PRENOM', '')} {attrs.get('NOM', '')}".strip()
            if name:
                lines.append(f"- Name: {name}")

        if attrs.get('ENT_COMPANY_NAME'):
            lines.append(f"- Company: {attrs['ENT_COMPANY_NAME']}")

        if contact.get('createdAt'):
            lines.append(f"- Created: {contact['createdAt']}")

        return "\n".join(lines) + "\n"

    def _format_company(self, company: Dict[str, Any]) -> str:
        """Format company information."""
        lines = []
        attrs = company.get('attributes', {})

        name = attrs.get('name', 'Unknown Company')
        lines.append(f"**Company:** {name}")

        if attrs.get('domain'):
            lines.append(f"- Domain: {attrs['domain']}")

        if attrs.get('industry'):
            lines.append(f"- Industry: {attrs['industry']}")

        if company.get('linkedContactsIds'):
            lines.append(f"- Linked Contacts: {len(company['linkedContactsIds'])}")

        return "\n".join(lines) + "\n"

    def _format_deal(self, deal: Dict[str, Any]) -> str:
        """Format deal information."""
        lines = []
        attrs = deal.get('attributes', {})

        deal_name = attrs.get('deal_name', 'Unnamed Deal')
        lines.append(f"**Deal:** {deal_name}")

        # Use deal_stage_name if available, otherwise fall back to deal_stage ID
        stage_name = attrs.get('deal_stage_name') or attrs.get('deal_stage')
        if stage_name:
            lines.append(f"- Stage: {stage_name}")

        if attrs.get('deal_value'):
            lines.append(f"- Value: {attrs['deal_value']}")

        if deal.get('linkedContactsIds'):
            lines.append(f"- Linked Contacts: {len(deal['linkedContactsIds'])}")

        if deal.get('linkedCompaniesIds'):
            lines.append(f"- Linked Companies: {len(deal['linkedCompaniesIds'])}")

        return "\n".join(lines) + "\n"

    def _format_note(self, note: Dict[str, Any]) -> str:
        """Format note information."""
        lines = []

        created = note.get('createdAt', 'Unknown date')
        lines.append(f"**Note ({created}):**")

        text = note.get('text', '')
        # Clean HTML tags for better readability
        import re
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()

        # Limit length
        if len(text) > 500:
            text = text[:500] + "..."

        lines.append(text)
        return "\n".join(lines) + "\n"

    def _format_task(self, task: Dict[str, Any]) -> str:
        """Format task information."""
        lines = []

        name = task.get('name', 'Unnamed task')
        due_date = task.get('date', 'No date')
        done = task.get('done', False)
        status = "✓ Done" if done else "○ Pending"

        lines.append(f"**{status}** {name} (Due: {due_date})")

        if task.get('notes'):
            notes = task['notes'][:200]
            lines.append(f"  Notes: {notes}")

        return "\n".join(lines) + "\n"

    def _extract_deal_name(self, enriched_data: Dict[str, Any]) -> str:
        """Extract deal name from enriched data."""
        primary_record = enriched_data.get("primary_record", {})
        attrs = primary_record.get("attributes", {})
        return attrs.get("deal_name", "Unknown Deal")

    def _extract_deal_id(self, enriched_data: Dict[str, Any]) -> str:
        """Extract deal ID from enriched data."""
        primary_record = enriched_data.get("primary_record", {})
        return str(primary_record.get("id", "unknown"))

    def _extract_company_name(self, enriched_data: Dict[str, Any]) -> Optional[str]:
        """Extract company name from enriched data."""
        # Try from primary record attributes
        primary_record = enriched_data.get("primary_record", {})
        attrs = primary_record.get("attributes", {})
        company_name = attrs.get("company_name")

        if company_name:
            return company_name

        # Try from related companies
        related_entities = enriched_data.get("related_entities", {})
        companies = related_entities.get("companies", [])
        if companies:
            first_company = companies[0]
            company_attrs = first_company.get("attributes", {})
            return company_attrs.get("name")

        return None

    def _build_fallback_summary(
        self,
        enriched_data: Dict[str, Any],
        raw_response: str
    ) -> DealSummary:
        """
        Build a basic fallback summary when AI parsing fails.

        Args:
            enriched_data: Original enriched data
            raw_response: Raw AI response

        Returns:
            Basic DealSummary
        """
        logger.warning("Building fallback summary")

        primary_record = enriched_data.get("primary_record", {})
        attrs = primary_record.get("attributes", {})

        return DealSummary(
            deal_name=attrs.get("deal_name", "Unknown Deal"),
            deal_id=str(primary_record.get("id", "unknown")),
            company_name=attrs.get("company_name", None),
            executive_summary="Summary generation failed. Please review raw data.",
            deal_context="An error occurred during AI summarization. Raw response: " + raw_response[:500],
            current_status="Unable to determine",
            next_steps_context="Manual review required",
            data_sources=["Script 1 enriched data"],
            confidence_score=0.0
        )
