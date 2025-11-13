"""
Cache manager for AI-generated deal summaries.

Caches summaries along with the enriched data used to generate them.
Provides intelligent cache invalidation based on data changes and age.
"""
import json
import hashlib
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class SummaryCache:
    """
    Manages caching of AI-generated summaries with change detection.

    Features:
    - Stores summary along with input enriched data
    - Detects data changes via hashing
    - Time-based cache invalidation (default: 24 hours)
    - Retrieves previous data for diff computation
    """

    def __init__(self, cache_file: Path, ttl_hours: int = 24):
        """
        Initialize cache manager.

        Args:
            cache_file: Path to SQLite cache database
            ttl_hours: Cache TTL in hours (default: 24)
        """
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours
        self._init_db()

    def _init_db(self):
        """Initialize cache database."""
        with sqlite3.connect(self.cache_file) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS summary_cache (
                    cache_key TEXT PRIMARY KEY,
                    enriched_data_hash TEXT NOT NULL,
                    prompt_hash TEXT NOT NULL,
                    enriched_data_json TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index for faster lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_key
                ON summary_cache(cache_key)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_generated_at
                ON summary_cache(generated_at)
            """)

            # Migration: Add prompt_hash column if it doesn't exist
            try:
                cursor = conn.execute("PRAGMA table_info(summary_cache)")
                columns = [row[1] for row in cursor.fetchall()]
                if 'prompt_hash' not in columns:
                    logger.info("Migrating cache database: adding prompt_hash column")
                    conn.execute("ALTER TABLE summary_cache ADD COLUMN prompt_hash TEXT DEFAULT 'legacy'")
                    logger.info("Migration complete")
            except Exception as e:
                logger.warning(f"Migration check failed: {e}")

            conn.commit()

    def _compute_data_hash(self, enriched_data: Dict[str, Any]) -> str:
        """
        Compute hash of enriched data for change detection.

        Ignores timestamp and metadata fields that change on every fetch.

        Args:
            enriched_data: Enriched CRM data

        Returns:
            SHA256 hash of the data
        """
        # Fields to ignore (timestamps and metadata that change on every fetch)
        IGNORED_FIELDS = {
            "updated_at", "updatedAt", "modified_at", "modifiedAt",
            "created_at", "createdAt", "last_fetched", "lastFetched",
            "last_modified", "lastModified", "timestamp", "fetched_at",
            "_metadata", "cache_time", "cacheTime",
            "metadata", "enrichment_timestamp", "duration_ms", "cache_hit_rate"
        }

        # Deep copy and remove ignored fields recursively
        def clean_dict(d: Any) -> Any:
            if isinstance(d, dict):
                return {k: clean_dict(v) for k, v in d.items() if k not in IGNORED_FIELDS}
            elif isinstance(d, list):
                return [clean_dict(item) for item in d]
            else:
                return d

        cleaned_data = clean_dict(enriched_data)
        data_str = json.dumps(cleaned_data, sort_keys=True)
        hash_result = hashlib.sha256(data_str.encode()).hexdigest()

        return hash_result

    def _compute_prompt_hash(self, prompt_template: str) -> str:
        """
        Compute MD5 hash of prompt template.

        Args:
            prompt_template: Prompt template string

        Returns:
            MD5 hash of the prompt (8 characters)
        """
        return hashlib.md5(prompt_template.encode()).hexdigest()[:8]

    def _get_cache_key(self, enriched_data: Dict[str, Any], prompt_hash: str) -> str:
        """
        Generate cache key from enriched data and prompt hash.

        Uses primary entity type, ID, and prompt hash to create unique key.

        Args:
            enriched_data: Enriched CRM data
            prompt_hash: MD5 hash of the prompt template

        Returns:
            Cache key string
        """
        primary_type = enriched_data.get("primary_type", "unknown")
        primary_record = enriched_data.get("primary_record", {})

        # Extract ID based on entity type
        if primary_type == "deal":
            entity_id = primary_record.get("id", "unknown")
        elif primary_type == "contact":
            entity_id = str(primary_record.get("id", primary_record.get("email", "unknown")))
        elif primary_type == "company":
            entity_id = primary_record.get("id", "unknown")
        else:
            entity_id = "unknown"

        return f"{primary_type}:{entity_id}:{prompt_hash}"

    def get_cached_summary(
        self,
        enriched_data: Dict[str, Any],
        prompt_template: str
    ) -> Optional[Tuple[Dict[str, Any], bool, Optional[Dict[str, Any]]]]:
        """
        Get cached summary if valid.

        Args:
            enriched_data: Enriched CRM data
            prompt_template: Prompt template string

        Returns:
            Tuple of (summary_dict, is_fresh, previous_enriched_data) if cache valid, None otherwise
            - is_fresh: True if data unchanged and cache < TTL
            - previous_enriched_data: Previous enriched data if cache exists but stale/changed
        """
        prompt_hash = self._compute_prompt_hash(prompt_template)
        cache_key = self._get_cache_key(enriched_data, prompt_hash)
        data_hash = self._compute_data_hash(enriched_data)

        try:
            with sqlite3.connect(self.cache_file) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT enriched_data_hash, prompt_hash, enriched_data_json, summary_json, generated_at
                    FROM summary_cache
                    WHERE cache_key = ?
                    ORDER BY generated_at DESC
                    LIMIT 1
                """, (cache_key,))

                row = cursor.fetchone()

                if not row:
                    logger.info(f"No cache found for {cache_key}")
                    return None

                cached_hash = row["enriched_data_hash"]
                cached_enriched = json.loads(row["enriched_data_json"])
                cached_summary = json.loads(row["summary_json"])
                generated_at = datetime.fromisoformat(row["generated_at"])

                # Check if data changed
                data_unchanged = (cached_hash == data_hash)

                # Check if cache is fresh (within TTL)
                age = datetime.now() - generated_at
                is_fresh = age < timedelta(hours=self.ttl_hours)

                logger.info(f"Cache found for {cache_key}: data_unchanged={data_unchanged}, age={age}, is_fresh={is_fresh}")
                if not data_unchanged:
                    logger.debug(f"Data hash mismatch: cached={cached_hash[:8]}, current={data_hash[:8]}")

                # Return cached summary only if data unchanged AND fresh
                if data_unchanged and is_fresh:
                    logger.info("Using fresh cached summary")
                    return (cached_summary, True, None)
                else:
                    # Return previous data for diff computation
                    logger.info("Cache stale or data changed, will recompute with diff")
                    return (cached_summary, False, cached_enriched)

        except Exception as e:
            logger.error(f"Error reading cache: {e}")
            return None

    def save_summary(
        self,
        enriched_data: Dict[str, Any],
        summary: Dict[str, Any],
        prompt_template: str
    ):
        """
        Save summary to cache.

        Args:
            enriched_data: Enriched CRM data used for generation
            summary: Generated summary
            prompt_template: Prompt template used for generation
        """
        prompt_hash = self._compute_prompt_hash(prompt_template)
        cache_key = self._get_cache_key(enriched_data, prompt_hash)
        data_hash = self._compute_data_hash(enriched_data)

        try:
            with sqlite3.connect(self.cache_file) as conn:
                # Insert or replace
                conn.execute("""
                    INSERT OR REPLACE INTO summary_cache
                    (cache_key, enriched_data_hash, prompt_hash, enriched_data_json, summary_json, generated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    cache_key,
                    data_hash,
                    prompt_hash,
                    json.dumps(enriched_data),
                    json.dumps(summary),
                    datetime.now().isoformat()
                ))
                conn.commit()
                logger.info(f"Saved summary to cache: {cache_key}")

        except Exception as e:
            logger.error(f"Error saving to cache: {e}")

    def clear_cache(self, cache_key: Optional[str] = None):
        """
        Clear cache entries.

        Args:
            cache_key: Specific cache key to clear, or None to clear all
        """
        try:
            with sqlite3.connect(self.cache_file) as conn:
                if cache_key:
                    conn.execute("DELETE FROM summary_cache WHERE cache_key = ?", (cache_key,))
                    logger.info(f"Cleared cache for {cache_key}")
                else:
                    conn.execute("DELETE FROM summary_cache")
                    logger.info("Cleared all cache")
                conn.commit()

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        try:
            with sqlite3.connect(self.cache_file) as conn:
                conn.row_factory = sqlite3.Row

                # Total entries
                cursor = conn.execute("SELECT COUNT(*) as total FROM summary_cache")
                total = cursor.fetchone()["total"]

                # Fresh entries (within TTL)
                cutoff = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()
                cursor = conn.execute("""
                    SELECT COUNT(*) as fresh
                    FROM summary_cache
                    WHERE generated_at > ?
                """, (cutoff,))
                fresh = cursor.fetchone()["fresh"]

                # Stale entries
                stale = total - fresh

                # Total size
                cursor = conn.execute("""
                    SELECT COALESCE(SUM(LENGTH(enriched_data_json) + LENGTH(summary_json)), 0) as size
                    FROM summary_cache
                """)
                size_bytes = cursor.fetchone()["size"]
                size_mb = size_bytes / (1024 * 1024)

                return {
                    "total_entries": total,
                    "fresh_entries": fresh,
                    "stale_entries": stale,
                    "total_size_mb": round(size_mb, 2),
                    "ttl_hours": self.ttl_hours
                }

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                "total_entries": 0,
                "fresh_entries": 0,
                "stale_entries": 0,
                "total_size_mb": 0.0,
                "ttl_hours": self.ttl_hours
            }
