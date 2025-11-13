"""
Core recommendation engine that integrates Scripts 1 & 2 with AI-powered action generation.
"""
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

# Import from Script 1 (brevo_data_gatherer)
from brevo_sales.config import load_config as load_script1_config
from brevo_sales.cache.manager import CacheManager as Script1Cache
from brevo_sales.enrichment.brevo_client import BrevoClient
from brevo_sales.enrichment.conversations_client import ConversationsClient
from brevo_sales.enrichment.enricher import DataEnricher

# Import from Script 2 (generate_deal_summary)
from brevo_sales.summarization.ai_client import AIClient
from brevo_sales.summarization.summarizer import DealSummarizer
from brevo_sales.summarization.cache import SummaryCache

# Local imports
from brevo_sales.recommendations.cache import RecommendationCache
from brevo_sales.recommendations.models import RecommendationResult
from brevo_sales.recommendations.context_loader import CompanyContextLoader
from brevo_sales.recommendations.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class ActionRecommender:
    """
    Generates prioritized next-best-action recommendations.
    
    Integrates:
    - Script 1: CRM data enrichment
    - Script 2: Deal summarization
    - Company context: ~/.brevo_sales_agent/company-context.md
    - AI: Claude for recommendation generation
    """

    def __init__(
        self,
        anthropic_api_key: str,
        brevo_api_key: str,
        cache: Optional[RecommendationCache] = None,
        prompt_template: Optional[str] = None
    ):
        """
        Initialize recommender.

        Args:
            anthropic_api_key: Anthropic API key for Claude
            brevo_api_key: Brevo API key for enrichment
            cache: Optional cache manager
            prompt_template: Optional custom prompt template
        """
        self.anthropic_api_key = anthropic_api_key
        self.brevo_api_key = brevo_api_key
        self.cache = cache

        # Load prompt and metadata
        if prompt_template:
            self.prompt_template = prompt_template
            self.prompt_metadata = {}
        else:
            prompt_path = Path(__file__).parent.parent / "prompts" / "recommend.md"
            self.prompt_metadata, self.prompt_template = PromptLoader.load_prompt_file_with_metadata(prompt_path)

        # Initialize AI client with settings from prompt metadata
        model = self.prompt_metadata.get("model", "claude-sonnet-4-20250514")
        temperature = self.prompt_metadata.get("temperature", 0.7)
        max_tokens = self.prompt_metadata.get("max_tokens", 4096)

        self.ai_client = AIClient(
            api_key=anthropic_api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

        logger.info(f"Initialized recommender with model={model}, temp={temperature}, max_tokens={max_tokens}")

    def recommend(
        self,
        deal_id: str,
        campaign_context: Optional[str] = None,
        force_refresh: bool = False
    ) -> RecommendationResult:
        """
        Generate recommendations for a deal.

        Args:
            deal_id: Deal ID to analyze
            campaign_context: Optional campaign-specific context
            force_refresh: Force regeneration even if cache is fresh

        Returns:
            RecommendationResult with prioritized actions
        """
        logger.info(f"Starting recommendation generation for deal {deal_id}")

        # Step 1: Load company context
        context_data = CompanyContextLoader.load_context()
        company_context = context_data["content"]
        logger.info(f"Loaded company context (version {context_data['version']})")

        # Step 2: Get enriched data from Script 1
        enriched_data = self._ensure_enriched_data(deal_id)
        logger.info("Enriched data loaded")

        # Step 3: Get summary from Script 2 (optional but recommended)
        summary = None
        try:
            summary = self._ensure_summary(enriched_data)
            logger.info("Summary loaded")
        except Exception as e:
            logger.warning(f"Could not generate summary: {e}")

        # Step 4: Check cache
        # Use summary's data_version for cache key stability (not affected by diff/timestamps)
        summary_for_cache = summary.get('data_version') if summary else None

        if self.cache and not force_refresh:
            cache_result = self.cache.get_cached_recommendation(
                deal_id=deal_id,
                enriched_data=enriched_data,
                summary=summary_for_cache,
                prompt_template=self.prompt_template,
                company_context=company_context,
                campaign_context=campaign_context
            )

            if cache_result:
                cached_rec, is_fresh, prev_enriched = cache_result
                if is_fresh:
                    logger.info("Using fresh cached recommendation")
                    result = RecommendationResult(**cached_rec)
                    result.is_cached = True
                    return result
                else:
                    logger.info("Cache found but stale, will regenerate")

        # Step 5: Build prompt with all context
        system_prompt = self._build_system_prompt(company_context)
        user_prompt = self._build_user_prompt(
            enriched_data=enriched_data,
            summary=summary,
            campaign_context=campaign_context
        )

        # Step 6: Generate recommendations using Claude
        logger.info("Calling Claude API for recommendations")
        response = self.ai_client.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format=None  # Markdown output
        )

        recommendations_markdown = response.get("response", "")
        logger.info(f"Generated recommendations ({len(recommendations_markdown)} chars)")

        # Step 7: Parse into structured result
        # For MVP, store as markdown. In production, parse into structured actions
        result = self._parse_recommendations(
            recommendations_markdown,
            enriched_data,
            context_data
        )

        # Step 8: Save to cache
        if self.cache:
            self.cache.save_recommendation(
                deal_id=deal_id,
                enriched_data=enriched_data,
                summary=summary_for_cache,
                prompt_template=self.prompt_template,
                company_context=company_context,
                campaign_context=campaign_context,
                recommendation=result.model_dump(mode='json')
            )
            logger.info("Saved recommendation to cache")

        return result

    def _ensure_enriched_data(self, deal_id: str) -> Dict[str, Any]:
        """
        Get enriched data from Script 1.

        Uses Script 1's caching automatically.
        """
        logger.info(f"Enriching deal data for {deal_id}")

        # Initialize Script 1 components
        config = load_script1_config()
        config.brevo.api_key = self.brevo_api_key

        cache = Script1Cache(config.cache_dir / "cache.db")
        brevo_client = BrevoClient(
            api_key=self.brevo_api_key,
            base_url=config.brevo.base_url,
            cache_manager=cache
        )

        # Initialize conversations client if cookie configured
        conversations_client = None
        if config.conversations.enabled and config.conversations.cookie_string:
            conversations_client = ConversationsClient(
                cookie_string=config.conversations.cookie_string,
                backend_url=config.conversations.backend_url,
                cache_manager=cache
            )

        # Initialize LinkedIn client if configured
        linkedin_client = None
        if config.linkedin.enabled and (config.linkedin.api_key or config.linkedin.pipedream_workflow_url):
            from brevo_sales.enrichment.linkedin_client import LinkedInClient
            linkedin_client = LinkedInClient(
                provider=config.linkedin.provider,
                cache_manager=cache,
                api_key=config.linkedin.api_key,
                pipedream_workflow_url=config.linkedin.pipedream_workflow_url
            )
            logger.info(f"LinkedIn client initialized with provider: {config.linkedin.provider}")

        # Initialize web search client if configured
        web_client = None
        if config.web_search.enabled and config.web_search.api_key:
            from brevo_sales.enrichment.web_client import WebSearchClient
            web_client = WebSearchClient(
                provider=config.web_search.provider,
                cache_manager=cache,
                api_key=config.web_search.api_key
            )
            logger.info(f"Web search client initialized with provider: {config.web_search.provider}")

        enricher = DataEnricher(
            brevo_client=brevo_client,
            linkedin_client=linkedin_client,
            web_client=web_client,
            conversations_client=conversations_client,
            cache_manager=cache  # Pass cache manager
        )

        # Enrich
        result = enricher.enrich(
            entity_identifier=deal_id,
            entity_type="deal"
        )

        return result.model_dump(mode='json')

    def _ensure_summary(self, enriched_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary from Script 2.

        Uses Script 2's caching automatically.
        """
        logger.info("Generating deal summary")

        # Initialize Script 2 components
        from brevo_sales.config import DEFAULT_CACHE_DIR
        cache_file = DEFAULT_CACHE_DIR / "summary_cache" / "summaries.db"
        cache = SummaryCache(cache_file)
        
        summarizer = DealSummarizer(
            ai_client=self.ai_client,
            cache=cache
        )

        # Summarize
        summary = summarizer.summarize(enriched_data)

        return summary.dict()

    def _build_system_prompt(self, company_context: str) -> str:
        """Build system prompt with company context."""
        # Process template variables
        prompt = PromptLoader.process_template_variables(
            self.prompt_template,
            {"company_context": company_context}
        )
        return prompt

    def _build_user_prompt(
        self,
        enriched_data: Dict[str, Any],
        summary: Optional[Dict[str, Any]],
        campaign_context: Optional[str]
    ) -> str:
        """Build user prompt with all context data."""
        parts = []

        # Header
        parts.append("# CRM Data and Context for Action Recommendations\n")

        # Campaign context if provided
        if campaign_context:
            parts.append(f"## Campaign Context\n{campaign_context}\n")

        # Summary if available
        if summary:
            parts.append(f"## Deal Summary\n{summary.get('executive_summary', 'N/A')}\n")

        # Enriched data (abbreviated for token efficiency)
        parts.append("## Enriched CRM Data\n")
        parts.append(self._format_enriched_data(enriched_data))

        # Instruction
        parts.append("\n---\n")
        parts.append("**Please analyze this data and provide your recommendation following the exact format specified in the system prompt:**")
        parts.append("- Section 1: DEAL OVERVIEW (max 10 lines, facts only)")
        parts.append("- Section 2: KEY HIGHLIGHTS (max 5 bullet points)")
        parts.append("- Section 3: NEXT ACTION (with subsections: ACTION DETAILS, COMPLETE CONTENT, PREREQUISITES, ASSUMPTIONS, SUCCESS METRICS, RATIONALE)")

        return "\n".join(parts)

    def _format_enriched_data(self, enriched_data: Dict[str, Any]) -> str:
        """Format enriched data for prompt."""
        primary_record = enriched_data.get("primary_record", {})
        related = enriched_data.get("related_entities", {})
        interactions = enriched_data.get("interaction_history", {})
        metadata = enriched_data.get("metadata", {})

        parts = []

        # Deal basics
        attrs = primary_record.get("attributes", {})
        parts.append(f"**Deal**: {attrs.get('deal_name', 'Unknown')}")
        parts.append(f"**Stage**: {attrs.get('deal_stage_name', attrs.get('deal_stage', 'Unknown'))}")
        if attrs.get("deal_value"):
            parts.append(f"**Value**: {attrs['deal_value']}")

        # Deal owner
        deal_owner = metadata.get("deal_owner")
        if deal_owner:
            parts.append(f"**Deal Owner**: {deal_owner['name']} ({deal_owner['email']})")

        # Contacts
        contacts = related.get("contacts", [])
        if contacts:
            parts.append(f"\n**Contacts** ({len(contacts)}):")
            for contact in contacts[:3]:
                email = contact.get("email", "N/A")
                name_attrs = contact.get("attributes", {})
                name = f"{name_attrs.get('PRENOM', '')} {name_attrs.get('NOM', '')}".strip()
                parts.append(f"- {name or email}")

        # Recent interactions
        notes = interactions.get("notes", [])
        if notes:
            parts.append(f"\n**Recent Notes** ({len(notes)}):")
            for note in notes[:3]:
                date = note.get("createdAt", "")[:10]
                text = note.get("text", "")[:100]
                parts.append(f"- {date}: {text}...")

        return "\n".join(parts)

    def _parse_recommendations(
        self,
        markdown: str,
        enriched_data: Dict[str, Any],
        context_data: Dict[str, Any]
    ) -> RecommendationResult:
        """
        Parse markdown recommendations into structured result.

        For MVP: Store markdown as-is. Production: Parse into structured actions.
        """
        primary_record = enriched_data.get("primary_record", {})
        attrs = primary_record.get("attributes", {})
        
        # Extract entity info
        deal_id = str(primary_record.get("id", "unknown"))
        deal_name = attrs.get("deal_name", "Unknown Deal")
        
        # Get first contact
        contacts = enriched_data.get("related_entities", {}).get("contacts", [])
        contact_name = None
        contact_email = None
        if contacts:
            first_contact = contacts[0]
            contact_attrs = first_contact.get("attributes", {})
            contact_name = f"{contact_attrs.get('PRENOM', '')} {contact_attrs.get('NOM', '')}".strip()
            contact_email = first_contact.get("email")

        # Compute data version hash
        import hashlib
        data_hash = hashlib.sha256(json.dumps(enriched_data, sort_keys=True).encode()).hexdigest()[:16]

        # Create result (simplified for MVP)
        from brevo_sales.recommendations.models import EngagementAnalysis
        
        result = RecommendationResult(
            deal_id=deal_id,
            deal_name=deal_name,
            contact_name=contact_name,
            contact_email=contact_email,
            analysis=EngagementAnalysis(
                engagement_score=75.0,  # Placeholder
                engagement_trend="stable",
                engagement_level="medium",
                interaction_frequency="weekly",  # Placeholder
                deal_stage=attrs.get("deal_stage_name", attrs.get("deal_stage")),
                key_insights=["Analysis available in full markdown output"]
            ),
            overall_strategy=markdown,  # Store full markdown
            data_version=data_hash,
            company_context_metadata={
                "version": context_data["version"],
                "hash": context_data["hash"]
            }
        )

        return result
