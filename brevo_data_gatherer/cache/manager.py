"""
Cache manager with TTL and change detection.
"""
import json
import hashlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

from brevo_data_gatherer.models.schemas import CacheEntry

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages caching with TTL (Time To Live) and change detection.

    Features:
    - Source-specific TTL (different expiry for different data sources)
    - SHA256 hashing for change detection
    - Automatic expiration cleanup
    - Cache hit/miss statistics
    """

    # Default TTL values in minutes
    TTL_CONFIG = {
        "brevo_crm": 15,          # Core CRM data changes moderately
        "brevo_notes": 5,          # Notes can be added frequently
        "brevo_tasks": 5,          # Tasks updated frequently
        "linkedin": 1440,          # LinkedIn data rarely changes (24h)
        "web_search": 1440,        # Web search cached for 24h
    }

    def __init__(self, db_path: Path):
        """Initialize cache manager with database path."""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database with schema."""
        schema_path = Path(__file__).parent / "schema.sql"

        with sqlite3.connect(self.db_path) as conn:
            with open(schema_path, 'r') as f:
                conn.executescript(f.read())
            conn.commit()

    def _make_cache_key(self, source: str, entity_type: str, entity_id: str) -> str:
        """Generate cache key from source, entity type, and entity ID."""
        return f"{source}:{entity_type}:{entity_id}"

    def _calculate_hash(self, data: Any) -> str:
        """Calculate SHA256 hash of data for change detection."""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def get(
        self,
        source: str,
        entity_type: str,
        entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve data from cache if not expired.

        Returns:
            Cached data if valid and not expired, None otherwise
        """
        cache_key = self._make_cache_key(source, entity_type, entity_id)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM cache
                WHERE cache_key = ? AND expires_at > datetime('now')
            """, (cache_key,))

            row = cursor.fetchone()

            if row:
                logger.info(f"Cache HIT: {cache_key}")
                return {
                    "data": json.loads(row["data_json"]),
                    "hash": row["data_hash"],
                    "cached_at": row["created_at"],
                    "expires_at": row["expires_at"]
                }

            logger.info(f"Cache MISS: {cache_key}")
            return None

    def set(
        self,
        source: str,
        entity_type: str,
        entity_id: str,
        data: Any,
        ttl_minutes: Optional[int] = None
    ) -> str:
        """
        Store data in cache with TTL.

        Args:
            source: Data source identifier
            entity_type: Type of entity (contact, deal, company)
            entity_id: Entity identifier
            data: Data to cache
            ttl_minutes: Custom TTL, or use default from TTL_CONFIG

        Returns:
            Data hash for change detection
        """
        cache_key = self._make_cache_key(source, entity_type, entity_id)
        data_hash = self._calculate_hash(data)
        data_json = json.dumps(data)

        if ttl_minutes is None:
            ttl_minutes = self.TTL_CONFIG.get(source, 60)  # Default 1 hour

        expires_at = datetime.now() + timedelta(minutes=ttl_minutes)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cache
                (cache_key, source, entity_type, entity_id, data_json, data_hash, ttl_minutes, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cache_key,
                source,
                entity_type,
                entity_id,
                data_json,
                data_hash,
                ttl_minutes,
                expires_at.isoformat()
            ))
            conn.commit()

        logger.info(f"Cache SET: {cache_key} (TTL: {ttl_minutes}m, expires: {expires_at})")
        return data_hash

    def has_changed(
        self,
        source: str,
        entity_type: str,
        entity_id: str,
        current_data: Any
    ) -> bool:
        """
        Check if data has changed since last cache.

        Returns:
            True if data changed or no cache exists, False if identical
        """
        cached = self.get(source, entity_type, entity_id)

        if not cached:
            return True  # No cache = treat as changed

        current_hash = self._calculate_hash(current_data)
        return current_hash != cached["hash"]

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM cache WHERE expires_at <= datetime('now')
            """)
            conn.commit()
            count = cursor.rowcount

        if count > 0:
            logger.info(f"Cleaned up {count} expired cache entries")

        return count

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Total entries
            cursor.execute("SELECT COUNT(*) as total FROM cache")
            total = cursor.fetchone()["total"]

            # Expired entries
            cursor.execute("""
                SELECT COUNT(*) as expired FROM cache
                WHERE expires_at <= datetime('now')
            """)
            expired = cursor.fetchone()["expired"]

            # Total size
            cursor.execute("""
                SELECT COALESCE(SUM(LENGTH(data_json)), 0) as total_size FROM cache
            """)
            total_size_bytes = cursor.fetchone()["total_size"]
            total_size_mb = total_size_bytes / (1024 * 1024)

            # By source
            cursor.execute("""
                SELECT source, COUNT(*) as count FROM cache
                GROUP BY source
            """)
            by_source = {row["source"]: row["count"] for row in cursor.fetchall()}

            return {
                "total_entries": total,
                "valid_entries": total - expired,
                "expired_entries": expired,
                "total_size_mb": total_size_mb,
                "by_source": by_source,
                "hit_rate": 0.0  # Will be calculated dynamically if tracking is added
            }

    def invalidate(self, source: str, entity_type: str, entity_id: str):
        """Invalidate (delete) a specific cache entry."""
        cache_key = self._make_cache_key(source, entity_type, entity_id)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache WHERE cache_key = ?", (cache_key,))
            conn.commit()

        logger.info(f"Cache INVALIDATED: {cache_key}")

    def invalidate_all(self, source: Optional[str] = None):
        """Invalidate all cache entries, optionally filtered by source."""
        with sqlite3.connect(self.db_path) as conn:
            if source:
                conn.execute("DELETE FROM cache WHERE source = ?", (source,))
                logger.info(f"Cache INVALIDATED: all {source} entries")
            else:
                conn.execute("DELETE FROM cache")
                logger.info("Cache INVALIDATED: all entries")
            conn.commit()

    def log_enrichment_run(
        self,
        entity_id: str,
        entity_type: str,
        sources_used: List[str],
        cache_hits: int,
        cache_misses: int,
        api_calls_made: int,
        duration_ms: int,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Log enrichment run statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO enrichment_runs
                (entity_id, entity_type, sources_used, cache_hits, cache_misses,
                 api_calls_made, total_duration_ms, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entity_id,
                entity_type,
                json.dumps(sources_used),
                cache_hits,
                cache_misses,
                api_calls_made,
                duration_ms,
                success,
                error_message
            ))
            conn.commit()
