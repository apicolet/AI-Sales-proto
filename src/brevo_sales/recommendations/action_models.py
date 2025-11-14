"""
Structured action models for executable recommendations.

Defines strict schemas for different action types (email, phone, LinkedIn, WhatsApp)
with validation to ensure actions are immediately executable without placeholders.
"""
import re
from datetime import datetime
from enum import Enum
from typing import List, Optional, Union, Literal, Annotated
from pydantic import BaseModel, Field, field_validator, EmailStr, HttpUrl, model_validator


# ============================================================================
# Enums
# ============================================================================

class ActionChannel(str, Enum):
    """Supported communication channels for actions."""
    EMAIL = "email"
    PHONE = "phone"
    LINKEDIN = "linkedin"
    WHATSAPP = "whatsapp"


class ActionStatus(str, Enum):
    """Status of an action in its lifecycle."""
    PENDING = "pending"
    PREREQUISITES_INCOMPLETE = "prerequisites_incomplete"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class PrerequisiteStatus(str, Enum):
    """Status of a prerequisite task."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


# ============================================================================
# Validators
# ============================================================================

def has_placeholders(text: str) -> bool:
    """
    Check if text contains common placeholder patterns.

    Detects patterns like:
    - [placeholder], {placeholder}, <placeholder>
    - {{variable}}, ${variable}
    - [NAME], [COMPANY], etc.
    - TODO, TBD, XXX markers
    """
    placeholder_patterns = [
        r'\[([A-Z_]+|\.\.\.)\]',  # [NAME], [COMPANY], [...]
        r'\{([A-Z_]+|\.\.\.)\}',  # {NAME}, {COMPANY}, {...}
        r'<([A-Z_]+|\.\.\.)>',    # <NAME>, <COMPANY>, <...>
        r'\{\{[^}]+\}\}',         # {{variable}}
        r'\$\{[^}]+\}',           # ${variable}
        r'\bTODO\b',              # TODO marker
        r'\bTBD\b',               # TBD marker
        r'\bXXX\b',               # XXX marker
        r'\[INSERT[^\]]*\]',      # [INSERT something]
        r'\[FILL[^\]]*\]',        # [FILL something]
    ]

    for pattern in placeholder_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    return False


# ============================================================================
# Prerequisite Model
# ============================================================================

class Prerequisite(BaseModel):
    """
    A prerequisite task that must be completed before executing the action.

    Attributes:
        id: Unique identifier for the prerequisite
        task: Description of what needs to be done (who, what, when)
        assignee: Person responsible for completing this task
        deadline: Optional deadline for completion
        status: Current status of the prerequisite
        blocking: If True, action cannot proceed until this is completed
    """
    id: str = Field(..., description="Unique identifier (e.g., 'prereq-1')")
    task: str = Field(..., min_length=10, description="Clear description of the task")
    assignee: Optional[str] = Field(None, description="Person responsible (name or email)")
    deadline: Optional[datetime] = Field(None, description="When this should be completed")
    status: PrerequisiteStatus = Field(
        default=PrerequisiteStatus.TODO,
        description="Current status"
    )
    blocking: bool = Field(
        default=True,
        description="Whether action can proceed without this"
    )

    @field_validator('task')
    @classmethod
    def task_must_not_have_placeholders(cls, v: str) -> str:
        """Ensure task description has no placeholders."""
        if has_placeholders(v):
            raise ValueError(f"Task description contains placeholders: {v}")
        return v


# ============================================================================
# Action Models
# ============================================================================

class EmailAction(BaseModel):
    """
    Email action with complete, ready-to-send content.

    All fields must be fully populated with no placeholders.
    """
    type: Literal[ActionChannel.EMAIL] = ActionChannel.EMAIL

    from_email: EmailStr = Field(..., description="Sender email address")
    from_name: str = Field(..., min_length=1, description="Sender display name")

    to_email: EmailStr = Field(..., description="Recipient email address")
    to_name: str = Field(..., min_length=1, description="Recipient name")

    subject: str = Field(..., min_length=5, description="Email subject line")
    content: str = Field(..., min_length=50, description="Complete email body (can be HTML or plain text)")

    cc_emails: List[EmailStr] = Field(default_factory=list, description="CC recipients")
    bcc_emails: List[EmailStr] = Field(default_factory=list, description="BCC recipients")

    attachments: List[HttpUrl] = Field(
        default_factory=list,
        description="URLs to attachment files"
    )

    @field_validator('subject', 'content', 'from_name', 'to_name')
    @classmethod
    def no_placeholders(cls, v: str) -> str:
        """Ensure critical fields have no placeholders."""
        if has_placeholders(v):
            raise ValueError(f"Field contains placeholders: {v[:100]}...")
        return v

    @model_validator(mode='after')
    def validate_email_completeness(self):
        """Ensure email is complete and actionable."""
        # Subject should be specific, not generic
        generic_subjects = ['hello', 'hi', 'follow up', 'checking in']
        if self.subject.lower().strip() in generic_subjects:
            raise ValueError(f"Subject line too generic: '{self.subject}'")

        return self


class PhoneAction(BaseModel):
    """
    Phone call action with complete talking points.
    """
    type: Literal[ActionChannel.PHONE] = ActionChannel.PHONE

    to_phone: str = Field(..., description="Phone number to call (E.164 format preferred)")
    to_name: str = Field(..., min_length=1, description="Person to call")

    objective: str = Field(..., min_length=10, description="Primary objective of the call")

    talking_points: List[str] = Field(
        ...,
        min_length=2,
        description="Key points to cover during the call"
    )

    expected_duration_minutes: int = Field(
        ...,
        ge=5,
        le=120,
        description="Expected duration in minutes"
    )

    notes: Optional[str] = Field(None, description="Additional context or notes")

    @field_validator('to_phone')
    @classmethod
    def validate_phone_format(cls, v: str) -> str:
        """Basic phone number validation."""
        # Remove common formatting characters
        cleaned = re.sub(r'[\s\-\(\)\.]+', '', v)

        # Check if it's mostly digits (allow leading +)
        if not re.match(r'^\+?\d{8,15}$', cleaned):
            raise ValueError(f"Invalid phone number format: {v}")

        return v

    @field_validator('objective', 'notes')
    @classmethod
    def no_placeholders(cls, v: Optional[str]) -> Optional[str]:
        """Ensure fields have no placeholders."""
        if v and has_placeholders(v):
            raise ValueError(f"Field contains placeholders: {v[:100]}...")
        return v

    @field_validator('talking_points')
    @classmethod
    def validate_talking_points(cls, v: List[str]) -> List[str]:
        """Ensure talking points are specific."""
        for point in v:
            if has_placeholders(point):
                raise ValueError(f"Talking point contains placeholders: {point}")
            if len(point) < 10:
                raise ValueError(f"Talking point too vague: {point}")
        return v


class LinkedInAction(BaseModel):
    """
    LinkedIn outreach action with complete message.
    """
    type: Literal[ActionChannel.LINKEDIN] = ActionChannel.LINKEDIN

    recipient_linkedin_url: HttpUrl = Field(
        ...,
        description="LinkedIn profile URL of recipient"
    )
    recipient_name: str = Field(..., min_length=1, description="Recipient's name")

    action_type: Literal["connection_request", "message", "inmail"] = Field(
        ...,
        description="Type of LinkedIn action"
    )

    subject: Optional[str] = Field(
        None,
        description="Subject line (for InMail only)"
    )

    message: str = Field(
        ...,
        min_length=20,
        max_length=1900,  # LinkedIn message limit
        description="Complete message content"
    )

    connection_note: Optional[str] = Field(
        None,
        max_length=300,  # LinkedIn connection note limit
        description="Note for connection request (max 300 chars)"
    )

    @field_validator('recipient_linkedin_url')
    @classmethod
    def validate_linkedin_url(cls, v: HttpUrl) -> HttpUrl:
        """Ensure URL is a valid LinkedIn profile."""
        url_str = str(v)
        if 'linkedin.com/in/' not in url_str:
            raise ValueError(f"Invalid LinkedIn profile URL: {url_str}")
        return v

    @field_validator('subject', 'message', 'connection_note', 'recipient_name')
    @classmethod
    def no_placeholders(cls, v: Optional[str]) -> Optional[str]:
        """Ensure fields have no placeholders."""
        if v and has_placeholders(v):
            raise ValueError(f"Field contains placeholders: {v[:100]}...")
        return v

    @model_validator(mode='after')
    def validate_action_requirements(self):
        """Ensure action type has required fields."""
        if self.action_type == "inmail" and not self.subject:
            raise ValueError("InMail requires a subject line")

        if self.action_type == "connection_request" and not self.connection_note:
            raise ValueError("Connection request should include a note")

        return self


class WhatsAppAction(BaseModel):
    """
    WhatsApp message action with complete content.
    """
    type: Literal[ActionChannel.WHATSAPP] = ActionChannel.WHATSAPP

    to_phone: str = Field(..., description="WhatsApp phone number (E.164 format)")
    to_name: str = Field(..., min_length=1, description="Recipient name")

    message: str = Field(
        ...,
        min_length=10,
        description="Complete message content"
    )

    media_url: Optional[HttpUrl] = Field(
        None,
        description="Optional media attachment URL (image, video, document)"
    )

    @field_validator('to_phone')
    @classmethod
    def validate_phone_format(cls, v: str) -> str:
        """Basic phone number validation (same as PhoneAction)."""
        cleaned = re.sub(r'[\s\-\(\)\.]+', '', v)
        if not re.match(r'^\+?\d{8,15}$', cleaned):
            raise ValueError(f"Invalid phone number format: {v}")
        return v

    @field_validator('message', 'to_name')
    @classmethod
    def no_placeholders(cls, v: str) -> str:
        """Ensure fields have no placeholders."""
        if has_placeholders(v):
            raise ValueError(f"Field contains placeholders: {v[:100]}...")
        return v


# ============================================================================
# Discriminated Union
# ============================================================================

ActionType = Annotated[
    Union[EmailAction, PhoneAction, LinkedInAction, WhatsAppAction],
    Field(discriminator='type')
]


# ============================================================================
# Executable Action Wrapper
# ============================================================================

class ExecutableAction(BaseModel):
    """
    Complete executable action with prerequisites and success metrics.

    This is the main model returned by the recommendation engine.
    """
    # Action details
    action: ActionType = Field(..., description="The specific action to execute")

    # Priority and timing
    priority: Literal["P0", "P1", "P2"] = Field(
        ...,
        description="Priority level (P0=urgent, P1=important, P2=nice-to-have)"
    )

    recommended_timing: str = Field(
        ...,
        description="When to execute (e.g., 'Within 24 hours', 'Tuesday morning')"
    )

    # Prerequisites
    prerequisites: List[Prerequisite] = Field(
        default_factory=list,
        description="Tasks that should be completed first"
    )

    # Context and rationale
    rationale: str = Field(
        ...,
        min_length=50,
        description="Why this action is recommended"
    )

    context: str = Field(
        ...,
        min_length=30,
        description="Relevant context from CRM data"
    )

    # Success metrics
    success_metrics: List[str] = Field(
        ...,
        min_length=1,
        description="How to measure success of this action"
    )

    # Metadata
    status: ActionStatus = Field(
        default=ActionStatus.PENDING,
        description="Current status of the action"
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When this action was generated"
    )

    @field_validator('rationale', 'context')
    @classmethod
    def no_placeholders(cls, v: str) -> str:
        """Ensure fields have no placeholders."""
        if has_placeholders(v):
            raise ValueError(f"Field contains placeholders: {v[:100]}...")
        return v

    @field_validator('success_metrics')
    @classmethod
    def validate_metrics(cls, v: List[str]) -> List[str]:
        """Ensure metrics are specific."""
        for metric in v:
            if has_placeholders(metric):
                raise ValueError(f"Success metric contains placeholders: {metric}")
            if len(metric) < 10:
                raise ValueError(f"Success metric too vague: {metric}")
        return v

    @model_validator(mode='after')
    def compute_status(self):
        """Automatically compute status based on prerequisites."""
        # If there are blocking prerequisites that aren't completed
        blocking_incomplete = any(
            p.blocking and p.status != PrerequisiteStatus.COMPLETED
            for p in self.prerequisites
        )

        if blocking_incomplete and self.status == ActionStatus.PENDING:
            self.status = ActionStatus.PREREQUISITES_INCOMPLETE
        elif not blocking_incomplete and self.status == ActionStatus.PREREQUISITES_INCOMPLETE:
            self.status = ActionStatus.READY

        return self


# ============================================================================
# Collection Model
# ============================================================================

class ActionRecommendations(BaseModel):
    """
    Collection of recommended actions with analysis.

    This is the top-level model returned by the recommend command.
    """
    # Deal context
    deal_id: str
    deal_name: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None

    # Analysis summary
    executive_summary: str = Field(
        ...,
        min_length=100,
        description="Brief overview of the deal situation"
    )

    key_insights: List[str] = Field(
        ...,
        min_length=1,
        description="Key facts and insights from CRM data"
    )

    # Recommended actions by priority
    p0_actions: List[ExecutableAction] = Field(
        default_factory=list,
        description="Urgent actions (do immediately)"
    )

    p1_actions: List[ExecutableAction] = Field(
        default_factory=list,
        description="Important actions (do this week)"
    )

    p2_actions: List[ExecutableAction] = Field(
        default_factory=list,
        description="Nice-to-have actions (do when possible)"
    )

    # Overall strategy
    overall_strategy: str = Field(
        ...,
        min_length=100,
        description="High-level engagement strategy"
    )

    # Metadata
    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="When these recommendations were generated"
    )

    data_version: str = Field(
        ...,
        description="Hash of the CRM data used"
    )

    is_cached: bool = Field(
        default=False,
        description="Whether this result came from cache"
    )

    @property
    def all_actions(self) -> List[ExecutableAction]:
        """Get all actions across all priorities."""
        return self.p0_actions + self.p1_actions + self.p2_actions

    @property
    def total_actions(self) -> int:
        """Total number of recommended actions."""
        return len(self.all_actions)

    @property
    def ready_actions(self) -> List[ExecutableAction]:
        """Get actions that are ready to execute (no blocking prerequisites)."""
        return [
            action for action in self.all_actions
            if action.status in (ActionStatus.READY, ActionStatus.PENDING)
        ]
