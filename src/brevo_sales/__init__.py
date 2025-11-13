"""
Brevo Sales AI Agent - Unified Package

A comprehensive suite for AI-powered sales engagement with Brevo CRM.

Modules:
- enrichment: Multi-source CRM data enrichment
- summarization: AI-powered deal summarization
- recommendations: Next-best-action recommendations with learning

Usage:
    # As CLI
    $ brevo-sales enrich contact@example.com
    $ brevo-sales summarize deal-id
    $ brevo-sales recommend deal-id

    # Programmatically
    from brevo_sales import DataEnricher, DealSummarizer, ActionRecommender
"""

__version__ = "1.0.0"
__author__ = "DTSL"

# Core exports from enrichment
from brevo_sales.enrichment.enricher import DataEnricher
from brevo_sales.enrichment.brevo_client import BrevoClient
from brevo_sales.enrichment.linkedin_client import LinkedInClient
from brevo_sales.enrichment.web_client import WebSearchClient

# Core exports from summarization
from brevo_sales.summarization.summarizer import DealSummarizer
from brevo_sales.summarization.ai_client import AIClient

# Core exports from recommendations
from brevo_sales.recommendations.recommender import ActionRecommender
from brevo_sales.recommendations.feedback_processor import FeedbackProcessor

# Configuration and cache
from brevo_sales.config import load_config, load_env_from_multiple_locations
from brevo_sales.cache.manager import CacheManager

__all__ = [
    # Enrichment
    "DataEnricher",
    "BrevoClient",
    "LinkedInClient",
    "WebSearchClient",

    # Summarization
    "DealSummarizer",
    "AIClient",

    # Recommendations
    "ActionRecommender",
    "FeedbackProcessor",

    # Utilities
    "load_config",
    "load_env_from_multiple_locations",
    "CacheManager",

    # Metadata
    "__version__",
]
