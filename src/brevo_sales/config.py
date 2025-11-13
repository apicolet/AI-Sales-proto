"""
Unified configuration management for brevo_sales package.
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv


def load_env_from_multiple_locations():
    """
    Load environment variables from multiple locations.

    Priority (last loaded wins):
    1. ~/.ai-sales/.env (global, lowest priority)
    2. ./.env (local, highest priority)

    This allows users to have a global config at ~/.ai-sales/.env
    and override it per-project with a local .env file.
    """
    # Load from global location first (lower priority)
    global_env = Path.home() / ".ai-sales" / ".env"
    if global_env.exists():
        load_dotenv(global_env, override=False)

    # Load from local location (higher priority, will override)
    local_env = Path(".env")
    if local_env.exists():
        load_dotenv(local_env, override=True)


class BrevoConfig(BaseModel):
    """Brevo API configuration."""
    api_key: str
    base_url: str = "https://api.brevo.com/v3"


class LinkedInConfig(BaseModel):
    """LinkedIn enrichment configuration."""
    enabled: bool = True
    provider: str = "pipedream"
    api_key: Optional[str] = None
    pipedream_workflow_url: Optional[str] = None


class WebSearchConfig(BaseModel):
    """Web search configuration."""
    enabled: bool = True
    provider: str = "serper"
    api_key: Optional[str] = None


class ConversationsConfig(BaseModel):
    """Conversations API configuration."""
    enabled: bool = True
    cookie_string: Optional[str] = None
    backend_url: str = "https://crm-backend-api.brevo.com"


class CacheTTLConfig(BaseModel):
    """Cache TTL configuration in minutes/hours."""
    # Enrichment caching
    brevo_crm: str = "15m"
    brevo_notes: str = "5m"
    brevo_tasks: str = "5m"
    brevo_conversations: str = "5m"
    brevo_users: str = "24h"
    linkedin: str = "24h"
    web_search: str = "24h"

    # Summarization caching
    summary: int = 1440  # 24 hours

    # Recommendation caching
    recommendations: int = 60  # 1 hour

    def get_minutes(self, key: str) -> int:
        """Convert time string to minutes."""
        value = getattr(self, key, "60m")
        if isinstance(value, int):
            return value
        if value.endswith("h"):
            return int(value[:-1]) * 60
        elif value.endswith("m"):
            return int(value[:-1])
        else:
            return int(value)  # Assume minutes


class Config(BaseModel):
    """Main configuration for brevo_sales package."""
    # Paths
    cache_dir: Path = Field(default_factory=lambda: Path.home() / ".brevo_sales_agent" / "cache")
    company_context_file: Path = Field(default_factory=lambda: Path.home() / ".brevo_sales_agent" / "company-context.md")

    # Logging
    log_level: str = "INFO"

    # API Configurations
    brevo: BrevoConfig
    anthropic_api_key: Optional[str] = None  # For AI features

    # Optional integrations
    linkedin: LinkedInConfig = Field(default_factory=LinkedInConfig)
    web_search: WebSearchConfig = Field(default_factory=WebSearchConfig)
    conversations: ConversationsConfig = Field(default_factory=ConversationsConfig)

    # Cache TTLs
    cache_ttl: CacheTTLConfig = Field(default_factory=CacheTTLConfig)

    class Config:
        arbitrary_types_allowed = True


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from YAML file and environment variables.

    Priority:
    1. Environment variables (highest)
    2. Config file
    3. Defaults (lowest)

    Environment variables:
    - BREVO_API_KEY (required for enrichment)
    - ANTHROPIC_API_KEY (required for summarization/recommendations)
    - LINKEDIN_PIPEDREAM_URL (optional)
    - SERPER_API_KEY (optional)
    - BREVO_COOKIE (optional)
    - CACHE_DIR (optional)
    - LOG_LEVEL (optional)
    """
    # Default config
    config_data: Dict[str, Any] = {
        "brevo": {
            "api_key": "",
            "base_url": "https://api.brevo.com/v3"
        }
    }

    # Load from file if provided
    if config_path and config_path.exists():
        with open(config_path, 'r') as f:
            file_config = yaml.safe_load(f)
            if file_config:
                config_data.update(file_config)

    # Override with environment variables
    if os.getenv("BREVO_API_KEY"):
        config_data.setdefault("brevo", {})["api_key"] = os.getenv("BREVO_API_KEY")

    if os.getenv("ANTHROPIC_API_KEY"):
        config_data["anthropic_api_key"] = os.getenv("ANTHROPIC_API_KEY")

    if os.getenv("LINKEDIN_API_KEY"):
        config_data.setdefault("linkedin", {})["api_key"] = os.getenv("LINKEDIN_API_KEY")

    if os.getenv("LINKEDIN_PIPEDREAM_URL"):
        config_data.setdefault("linkedin", {})["pipedream_workflow_url"] = os.getenv("LINKEDIN_PIPEDREAM_URL")

    if os.getenv("SERPER_API_KEY"):
        config_data.setdefault("web_search", {})["api_key"] = os.getenv("SERPER_API_KEY")

    if os.getenv("BREVO_COOKIE"):
        config_data.setdefault("conversations", {})["cookie_string"] = os.getenv("BREVO_COOKIE")

    if os.getenv("CACHE_DIR"):
        config_data["cache_dir"] = Path(os.getenv("CACHE_DIR"))

    if os.getenv("LOG_LEVEL"):
        config_data["log_level"] = os.getenv("LOG_LEVEL")

    return Config(**config_data)


# Default paths
DEFAULT_CACHE_DIR = Path.home() / ".brevo_sales_agent"
DEFAULT_COMPANY_CONTEXT = DEFAULT_CACHE_DIR / "company-context.md"
DEFAULT_RECOMMENDATION_CACHE = DEFAULT_CACHE_DIR / "recommendation_cache.db"
