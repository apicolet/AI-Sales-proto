"""
Pydantic data models for type-safe data handling.

This package contains all data models used throughout the application:
- Brevo CRM entities (Contact, Company, Deal, Note, Task)
- LinkedIn enrichment data (Profile, Company)
- Web search results and company intelligence
- Enriched data output structure
- Cache metadata
"""

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
    EnrichedData,
    CacheEntry,
    EnrichmentRun
)

__all__ = [
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
    "CacheEntry",
    "EnrichmentRun",
]
