"""
Brevo Data Gatherer - Script 1: Non-AI Data Enrichment

A Python package for enriching Brevo CRM entities (contacts, deals, companies)
with data from multiple sources including LinkedIn and web search.

Key Features:
- Multi-source data enrichment (Brevo API, LinkedIn, Web Search)
- Intelligent caching with source-specific TTLs
- Auto-detection of entity types
- Complete data preservation (no summarization)
- CLI interface for easy usage

Usage:
    from brevo_data_gatherer import DataEnricher, BrevoClient, CacheManager
    from brevo_data_gatherer.config import load_config

    # Load configuration
    config = load_config()

    # Initialize clients
    cache_manager = CacheManager(config.cache_dir)
    brevo_client = BrevoClient(config.brevo.api_key, config.brevo.base_url, cache_manager)

    # Create enricher
    enricher = DataEnricher(brevo_client=brevo_client, cache_manager=cache_manager)

    # Enrich an entity
    data = enricher.enrich("contact@example.com")

CLI Usage:
    $ brevo-enrich contact@example.com
    $ brevo-enrich 61a5ce58c5d4795761045990 --type deal -o deal_data.json
"""

__version__ = "1.0.0"
__author__ = "DTSL"

# Core exports
from brevo_data_gatherer.core.enricher import DataEnricher
from brevo_data_gatherer.core.brevo_client import BrevoClient
from brevo_data_gatherer.core.linkedin_client import LinkedInClient
from brevo_data_gatherer.core.web_client import WebSearchClient

# Cache exports
from brevo_data_gatherer.cache.manager import CacheManager

# Model exports
from brevo_data_gatherer.models.schemas import (
    BrevoContact,
    BrevoCompany,
    BrevoDeal,
    BrevoNote,
    BrevoTask,
    LinkedInProfile,
    LinkedInCompany,
    WebSearchResult,
    CompanyIntelligence,
    EnrichedData
)

# Configuration exports
from brevo_data_gatherer.config import (
    Config,
    BrevoConfig,
    LinkedInConfig,
    WebSearchConfig,
    load_config,
    create_default_config_file
)

__all__ = [
    # Core classes
    "DataEnricher",
    "BrevoClient",
    "LinkedInClient",
    "WebSearchClient",
    "CacheManager",

    # Data models
    "BrevoContact",
    "BrevoCompany",
    "BrevoDeal",
    "BrevoNote",
    "BrevoTask",
    "LinkedInProfile",
    "LinkedInCompany",
    "WebSearchResult",
    "CompanyIntelligence",
    "EnrichedData",

    # Configuration
    "Config",
    "BrevoConfig",
    "LinkedInConfig",
    "WebSearchConfig",
    "load_config",
    "create_default_config_file",

    # Version
    "__version__",
]
