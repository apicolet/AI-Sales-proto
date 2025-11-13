"""
Configuration utilities for generate_deal_summary.
"""
from pathlib import Path
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
