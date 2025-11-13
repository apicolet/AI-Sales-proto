"""
Pydantic models for data validation and type safety.
"""
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field


class BrevoContact(BaseModel):
    """Brevo contact data model."""
    id: int
    email: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    emailBlacklisted: bool = False
    smsBlacklisted: bool = False
    listIds: List[int] = Field(default_factory=list)
    createdAt: Optional[datetime] = None
    modifiedAt: Optional[datetime] = None


class BrevoCompany(BaseModel):
    """Brevo company data model."""
    id: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    linkedContactsIds: List[int] = Field(default_factory=list)
    linkedDealsIds: List[str] = Field(default_factory=list)
    createdAt: Optional[datetime] = None


class BrevoDeal(BaseModel):
    """Brevo deal data model."""
    id: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    linkedContactsIds: List[int] = Field(default_factory=list)
    linkedCompaniesIds: List[str] = Field(default_factory=list)
    createdAt: Optional[datetime] = None


class BrevoNote(BaseModel):
    """Brevo note data model."""
    id: str
    text: str
    contactIds: List[int] = Field(default_factory=list)
    dealIds: List[str] = Field(default_factory=list)
    companyIds: List[str] = Field(default_factory=list)
    createdAt: Optional[datetime] = None


class BrevoTask(BaseModel):
    """Brevo task data model."""
    id: str
    name: str
    taskTypeId: str
    date: Optional[datetime] = None
    notes: Optional[str] = None
    done: bool = False
    assignToId: Optional[str] = None
    contactsIds: List[int] = Field(default_factory=list)
    dealsIds: List[str] = Field(default_factory=list)
    companiesIds: List[str] = Field(default_factory=list)
    createdAt: Optional[datetime] = None


class LinkedInProfile(BaseModel):
    """LinkedIn profile data model."""
    person_id: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    headline: Optional[str] = None
    industry: Optional[str] = None
    locationName: Optional[str] = None
    summary: Optional[str] = None
    profilePictureUrl: Optional[str] = None
    publicProfileUrl: Optional[str] = None


class LinkedInCompany(BaseModel):
    """LinkedIn company data model."""
    organization_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    industries: List[str] = Field(default_factory=list)
    specialties: List[str] = Field(default_factory=list)
    followerCount: Optional[int] = None
    employeeCount: Optional[int] = None


class WebSearchResult(BaseModel):
    """Web search result data model."""
    title: str
    url: str
    snippet: str
    date: Optional[str] = None
    relevanceScore: Optional[float] = None


class CompanyIntelligence(BaseModel):
    """Company intelligence from web research."""
    source: str = "web_research"
    key_facts: List[str] = Field(default_factory=list)
    tech_stack: List[Dict[str, Any]] = Field(default_factory=list)
    recent_news: List[Dict[str, Any]] = Field(default_factory=list)


class ConversationMessage(BaseModel):
    """Email message from Brevo conversations."""
    date: Optional[str] = None
    contact_id: Optional[int] = None
    visitor_name: Optional[str] = None
    conversation_id: Optional[str] = None
    thread_link: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    to_email: Optional[str] = None
    to_name: Optional[str] = None
    subject: Optional[str] = None
    html_body: Optional[str] = None
    created_at: Optional[Union[str, int]] = None  # Can be string or Unix timestamp (int)
    message_type: Optional[str] = None  # 'agent' or 'visitor'
    agent_name: Optional[str] = None


class ConversationEmail(BaseModel):
    """Email conversation grouping multiple messages."""
    conversation_id: str
    thread_link: Optional[str] = None
    contact_id: Optional[int] = None
    visitor_name: Optional[str] = None
    messages: List[ConversationMessage] = Field(default_factory=list)
    first_message_date: Optional[str] = None
    last_message_date: Optional[str] = None
    message_count: int = 0


class EnrichedData(BaseModel):
    """Complete enriched data output."""
    primary_type: str = Field(..., description="contact, deal, or company")
    primary_record: Dict[str, Any]

    related_entities: Dict[str, List[Any]] = Field(
        default_factory=lambda: {
            "contacts": [],
            "companies": [],
            "deals": []
        }
    )

    interaction_history: Dict[str, List[Any]] = Field(
        default_factory=lambda: {
            "notes": [],
            "tasks": [],
            "call_summaries": [],
            "conversations": []
        }
    )

    enrichment: Dict[str, Any] = Field(
        default_factory=lambda: {
            "linkedin_profiles": {"contacts": [], "company": None},
            "company_intelligence": None,
            "web_research": []
        }
    )

    metadata: Dict[str, Any] = Field(
        default_factory=lambda: {
            "enrichment_timestamp": None,
            "api_calls_made": 0,
            "data_quality": "unknown",
            "sources_used": [],
            "cache_hit_rate": 0.0
        }
    )


class CacheEntry(BaseModel):
    """Cache entry data model."""
    cache_key: str
    source: str
    entity_type: str
    entity_id: str
    data_json: str
    data_hash: str
    created_at: datetime
    ttl_minutes: int
    expires_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EnrichmentRun(BaseModel):
    """Enrichment run metadata."""
    entity_id: str
    entity_type: str
    run_timestamp: datetime
    sources_used: List[str]
    cache_hits: int = 0
    cache_misses: int = 0
    api_calls_made: int = 0
    total_duration_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None
