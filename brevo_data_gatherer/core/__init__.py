"""
Core modules for Brevo data enrichment.

This package contains the main business logic for data enrichment:
- enricher: Main orchestrator coordinating all data gathering
- brevo_client: Brevo API client wrapper with caching
- linkedin_client: LinkedIn enrichment via Pipedream workflows
- web_client: Web search for company intelligence
"""

from brevo_data_gatherer.core.enricher import DataEnricher
from brevo_data_gatherer.core.brevo_client import BrevoClient
from brevo_data_gatherer.core.linkedin_client import LinkedInClient
from brevo_data_gatherer.core.web_client import WebSearchClient

__all__ = [
    "DataEnricher",
    "BrevoClient",
    "LinkedInClient",
    "WebSearchClient",
]
