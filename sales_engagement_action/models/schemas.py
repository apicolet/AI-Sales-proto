"""
Data models for sales engagement action recommendations.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class TimingRecommendation(BaseModel):
    """When to execute an action."""
    recommendation: str  # "today", "this-week", "next-week"
    specific_datetime: Optional[str] = None  # ISO format or relative "tomorrow 10am"
    timezone: str = "UTC"
    urgency: str  # "high", "medium", "low"
    rationale: str  # Why this timing


class ActionContent(BaseModel):
    """Full ready-to-send content for P0 actions."""
    # Email-specific
    subject: Optional[str] = None
    body: str
    
    # Call-specific
    call_script: Optional[str] = None
    talking_points: Optional[List[str]] = None
    
    # Common fields
    call_to_action: str
    tone: str  # "consultative", "friendly", "professional", "urgent"
    estimated_duration: Optional[str] = None  # For calls
    personalization_notes: List[str] = Field(default_factory=list)


class ActionOutline(BaseModel):
    """High-level outline for P1/P2 actions."""
    key_points: List[str]
    approach: str
    considerations: List[str] = Field(default_factory=list)
    note: str = "Full content available on request"


class ActionRecommendation(BaseModel):
    """Single action recommendation."""
    id: str  # Unique identifier like "rec_001"
    priority: str  # "P0", "P1", "P2"
    channel: str  # "email", "phone", "linkedin", "whatsapp"
    action_type: str  # "follow_up", "introduction", "value_share", etc.
    action_title: str  # Brief description
    
    # Content (mutually exclusive based on priority)
    content: Optional[ActionContent] = None  # Full content for P0
    outline: Optional[ActionOutline] = None  # Brief outline for P1/P2
    
    # Metadata
    prerequisites: List[str] = Field(default_factory=list)
    timing: TimingRecommendation
    rationale: str  # 2-3 sentences on why THIS action, why NOW
    next_steps: str  # What happens after this action
    confidence_score: float = Field(ge=0, le=100)  # 0-100
    success_probability: float = Field(ge=0, le=100)  # 0-100
    
    # Context applied
    company_context_applied: List[str] = Field(default_factory=list)


class EngagementAnalysis(BaseModel):
    """Analysis of engagement patterns."""
    engagement_score: float = Field(ge=0, le=100)
    engagement_trend: str  # "increasing", "stable", "decreasing"
    engagement_level: str  # "high", "medium", "low"
    
    last_interaction: Optional[str] = None  # ISO datetime
    last_interaction_days_ago: Optional[int] = None
    interaction_frequency: str  # "daily", "weekly", "monthly", "rarely"
    response_rate: Optional[float] = None  # 0-1
    
    preferred_channels: List[str] = Field(default_factory=list)
    key_themes: List[str] = Field(default_factory=list)
    
    # Deal context
    deal_health: Optional[str] = None  # "healthy", "at-risk", "stale"
    deal_stage: Optional[str] = None
    days_in_stage: Optional[int] = None
    
    # Tasks
    open_tasks: int = 0
    overdue_tasks: int = 0
    
    # Insights
    key_insights: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    triggers: List[str] = Field(default_factory=list)


class RecommendationResult(BaseModel):
    """Complete recommendation output."""
    # Entity info
    deal_id: str
    deal_name: str
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    
    # Analysis
    analysis: EngagementAnalysis
    
    # Actions by priority
    p0_actions: List[ActionRecommendation] = Field(default_factory=list)  # 1-2 actions with full content
    p1_actions: List[ActionRecommendation] = Field(default_factory=list)  # 2-3 actions with outlines
    p2_actions: List[ActionRecommendation] = Field(default_factory=list)  # 1-3 actions with outlines
    
    # Strategy
    overall_strategy: str
    success_criteria: List[str] = Field(default_factory=list)
    
    # Campaign context
    campaign_context_applied: Optional[Dict[str, Any]] = None
    
    # Company context
    company_context_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    data_version: str  # Hash of enriched data
    is_cached: bool = False
    previous_recommendation_date: Optional[str] = None
    changes_since_last: Optional[str] = None


class FeedbackInput(BaseModel):
    """User feedback on a recommendation."""
    recommendation_id: str
    action_priority: str  # "P0", "P1", "P2"
    action_channel: str  # "email", "phone", "linkedin", "whatsapp"
    
    feedback_type: str  # "positive", "negative", "neutral"
    feedback_text: str
    
    # Optional detailed feedback
    what_worked: Optional[str] = None
    what_didnt_work: Optional[str] = None
    suggested_improvement: Optional[str] = None
    
    # Metadata
    deal_id: Optional[str] = None
    submitted_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class FeedbackResult(BaseModel):
    """Result of processing feedback."""
    status: str  # "success", "error"
    learning_extracted: str
    added_to_section: str
    company_context_updated: bool
    new_version: Optional[str] = None
    will_apply_to: str
    error_message: Optional[str] = None
