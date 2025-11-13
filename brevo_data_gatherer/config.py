"""
Configuration management for brevo_data_gatherer.
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
    provider: str = "pipedream"  # or "direct"
    api_key: Optional[str] = None
    pipedream_workflow_url: Optional[str] = None


class WebSearchConfig(BaseModel):
    """Web search configuration."""
    enabled: bool = True
    provider: str = "serper"  # or "google"
    api_key: Optional[str] = None


class ConversationsConfig(BaseModel):
    """Conversations API configuration."""
    enabled: bool = True
    cookie_string: Optional[str] = None
    backend_url: str = "https://crm-backend-api.brevo.com"


class CacheTTLConfig(BaseModel):
    """Cache TTL configuration in minutes/hours."""
    brevo_crm: str = "15m"
    brevo_notes: str = "5m"
    brevo_tasks: str = "5m"
    brevo_conversations: str = "5m"
    brevo_users: str = "24h"
    linkedin: str = "24h"
    web_search: str = "24h"

    def get_minutes(self, key: str) -> int:
        """Convert time string to minutes."""
        value = getattr(self, key, "60m")
        if value.endswith("h"):
            return int(value[:-1]) * 60
        elif value.endswith("m"):
            return int(value[:-1])
        else:
            return int(value)  # Assume minutes


class Config(BaseModel):
    """Main configuration."""
    cache_dir: Path = Field(default_factory=lambda: Path.home() / ".brevo_sales_agent" / "cache")
    log_level: str = "INFO"
    brevo: BrevoConfig
    linkedin: LinkedInConfig = Field(default_factory=LinkedInConfig)
    web_search: WebSearchConfig = Field(default_factory=WebSearchConfig)
    conversations: ConversationsConfig = Field(default_factory=ConversationsConfig)
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
    - BREVO_API_KEY
    - LINKEDIN_API_KEY (optional)
    - LINKEDIN_PIPEDREAM_URL (optional)
    - SERPER_API_KEY (optional)
    - CACHE_DIR (optional)
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


def create_default_config_file(output_path: Path):
    """Create a default configuration file with placeholders."""
    default_config = {
        "cache_dir": "~/.brevo_sales_agent/cache",
        "log_level": "INFO",
        "brevo": {
            "api_key": "${BREVO_API_KEY}",
            "base_url": "https://api.brevo.com/v3"
        },
        "linkedin": {
            "enabled": True,
            "provider": "pipedream",
            "api_key": "${LINKEDIN_API_KEY}",
            "pipedream_workflow_url": "${LINKEDIN_PIPEDREAM_URL}"
        },
        "web_search": {
            "enabled": True,
            "provider": "serper",
            "api_key": "${SERPER_API_KEY}"
        },
        "conversations": {
            "enabled": True,
            "cookie_string": "${BREVO_COOKIE}",
            "backend_url": "https://crm-backend-api.brevo.com"
        },
        "cache_ttl": {
            "brevo_crm": "15m",
            "brevo_notes": "5m",
            "brevo_tasks": "5m",
            "brevo_conversations": "5m",
            "linkedin": "24h",
            "web_search": "24h"
        }
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

    print(f"Created default config at: {output_path}")
    print("\nPlease set the following environment variables:")
    print("  export BREVO_API_KEY='your-brevo-api-key'")
    print("  export BREVO_COOKIE='your-brevo-cookie-string'  # optional, for conversations")
    print("  export LINKEDIN_API_KEY='your-linkedin-key'  # optional")
    print("  export LINKEDIN_PIPEDREAM_URL='your-pipedream-workflow-url'  # optional")
    print("  export SERPER_API_KEY='your-serper-api-key'  # optional")
