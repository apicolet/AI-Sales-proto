"""
Configuration management for sales_engagement_action.
"""
import os
from pathlib import Path
from typing import Optional
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


class CacheTTLConfig(BaseModel):
    """Cache TTL configuration in minutes."""
    recommendations: int = 60  # 1 hour (recommendations become stale quickly)
    enriched_data: int = 15    # 15 minutes (from Script 1)
    summary: int = 1440         # 24 hours (from Script 2)


class Config(BaseModel):
    """Main configuration for sales engagement action."""
    # API Keys
    anthropic_api_key: str
    brevo_api_key: str
    
    # Paths
    cache_dir: Path = Field(default_factory=lambda: Path.home() / ".brevo_sales_agent")
    company_context_file: Path = Field(default_factory=lambda: Path.home() / ".brevo_sales_agent" / "company-context.md")
    
    # Cache TTL
    cache_ttl: CacheTTLConfig = Field(default_factory=CacheTTLConfig)
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        arbitrary_types_allowed = True


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from environment variables.
    
    Environment variables:
    - ANTHROPIC_API_KEY (required)
    - BREVO_API_KEY (required)
    - CACHE_DIR (optional)
    - LOG_LEVEL (optional)
    """
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is required")
    
    brevo_api_key = os.getenv("BREVO_API_KEY")
    if not brevo_api_key:
        raise ValueError("BREVO_API_KEY environment variable is required")
    
    config_data = {
        "anthropic_api_key": anthropic_api_key,
        "brevo_api_key": brevo_api_key,
    }
    
    if os.getenv("CACHE_DIR"):
        config_data["cache_dir"] = Path(os.getenv("CACHE_DIR"))
    
    if os.getenv("LOG_LEVEL"):
        config_data["log_level"] = os.getenv("LOG_LEVEL")
    
    return Config(**config_data)


# Default paths
DEFAULT_CACHE_DIR = Path.home() / ".brevo_sales_agent"
DEFAULT_COMPANY_CONTEXT = DEFAULT_CACHE_DIR / "company-context.md"
DEFAULT_RECOMMENDATION_CACHE = DEFAULT_CACHE_DIR / "recommendation_cache.db"
