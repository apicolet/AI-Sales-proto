"""
Cache manager for recommendation results with intelligent invalidation.

Tracks 5 dependencies:
1. Enriched data hash (from Script 1)
2. Summary hash (from Script 2, optional)
3. Prompt hash (from prompt template files)
4. Company context hash (from ~/.brevo_sales_agent/company-context.md)
5. Campaign context hash (optional input)
"""
import json
import hashlib
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class RecommendationCache:
    """Manages caching of AI-generated recommendations with multi-dependency tracking."""

    def __init__(self, cache_file: Path, ttl_minutes: int = 60):
        """
        Initialize cache manager.

        Args:
            cache_file: Path to SQLite cache database
            ttl_minutes: Cache TTL in minutes (default: 60 minutes = 1 hour)
        """
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_minutes = ttl_minutes
        self._init_db()

    def _init_db(self):
        """Initialize cache database with schema."""
        with sqlite3.connect(self.cache_file) as conn:
            # Main recommendation cache
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recommendation_cache (
                    cache_key TEXT PRIMARY KEY,
                    enriched_data_hash TEXT NOT NULL,
                    summary_hash TEXT,
                    prompt_hash TEXT NOT NULL,
                    company_context_hash TEXT NOT NULL,
                    campaign_context_hash TEXT,
                    enriched_data_json TEXT NOT NULL,
                    summary_json TEXT,
                    recommendation_json TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Feedback log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recommendation_id TEXT NOT NULL,
                    deal_id TEXT NOT NULL,
                    action_priority TEXT NOT NULL,
                    action_channel TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    feedback_text TEXT,
                    what_worked TEXT,
                    what_didnt_work TEXT,
                    suggested_improvement TEXT,
                    recorded_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Context updates log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS context_updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_type TEXT NOT NULL,
                    section TEXT NOT NULL,
                    content TEXT NOT NULL,
                    applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    source_feedback_id INTEGER,
                    FOREIGN KEY (source_feedback_id) REFERENCES feedback_log(id)
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_key ON recommendation_cache(cache_key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON recommendation_cache(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_deal ON feedback_log(deal_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_time ON feedback_log(recorded_at)")

            conn.commit()

    def _compute_hash(self, data: Any) -> str:
        """Compute SHA256 hash of data."""
        if isinstance(data, str):
            data_str = data
        else:
            data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]

    def _get_cache_key(
        self,
        deal_id: str,
        prompt_hash: str,
        company_context_hash: str,
        campaign_context_hash: Optional[str]
    ) -> str:
        """Generate cache key from identifiers."""
        base = f"deal:{deal_id}:prompt:{prompt_hash}:context:{company_context_hash}"
        if campaign_context_hash:
            base += f":campaign:{campaign_context_hash}"
        return base

    def get_cached_recommendation(
        self,
        deal_id: str,
        enriched_data: Dict[str, Any],
        summary: Optional[str],  # Changed to str: expects summary['data_version'] hash
        prompt_template: str,
        company_context: str,
        campaign_context: Optional[str]
    ) -> Optional[Tuple[Dict[str, Any], bool, Optional[Dict[str, Any]]]]:
        """
        Get cached recommendation if valid.

        Returns:
            Tuple of (recommendation_dict, is_fresh, previous_enriched_data) if cache exists
            - is_fresh: True if all hashes match and TTL valid
            - previous_enriched_data: Previous data if cache exists but stale/changed
        """
        # Compute current hashes
        # Exclude metadata field from enriched_data hash (contains timestamps)
        enriched_data_stable = {k: v for k, v in enriched_data.items() if k != 'metadata'}
        enriched_hash = self._compute_hash(enriched_data_stable)
        summary_hash = summary if summary else None  # summary is already a hash string (data_version)
        prompt_hash = self._compute_hash(prompt_template)
        context_hash = self._compute_hash(company_context)
        campaign_hash = self._compute_hash(campaign_context) if campaign_context else None

        cache_key = self._get_cache_key(deal_id, prompt_hash, context_hash, campaign_hash)

        try:
            with sqlite3.connect(self.cache_file) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT enriched_data_hash, summary_hash, prompt_hash, 
                           company_context_hash, campaign_context_hash,
                           enriched_data_json, recommendation_json, generated_at, expires_at
                    FROM recommendation_cache
                    WHERE cache_key = ?
                    ORDER BY generated_at DESC
                    LIMIT 1
                """, (cache_key,))

                row = cursor.fetchone()

                if not row:
                    logger.info(f"No cache found for {cache_key}")
                    return None

                # Check if all hashes match
                # Note: We don't check summary_hash to avoid cache invalidation from Script 2's diff tracking
                hashes_match = (
                    row["enriched_data_hash"] == enriched_hash and
                    row["prompt_hash"] == prompt_hash and
                    row["company_context_hash"] == context_hash and
                    (row["campaign_context_hash"] == campaign_hash if campaign_context else True)
                )

                # Check if TTL expired
                expires_at = datetime.fromisoformat(row["expires_at"])
                is_expired = datetime.now() > expires_at

                # Calculate age
                generated_at = datetime.fromisoformat(row["generated_at"])
                age = datetime.now() - generated_at

                logger.info(
                    f"Cache found for {cache_key}: "
                    f"hashes_match={hashes_match}, expired={is_expired}, age={age}"
                )

                # Return cached if fresh
                if hashes_match and not is_expired:
                    logger.info("Using fresh cached recommendation")
                    cached_recommendation = json.loads(row["recommendation_json"])
                    return (cached_recommendation, True, None)
                else:
                    # Return previous data for diff
                    logger.info("Cache stale or data changed, will regenerate")
                    cached_recommendation = json.loads(row["recommendation_json"])
                    previous_enriched = json.loads(row["enriched_data_json"])
                    return (cached_recommendation, False, previous_enriched)

        except Exception as e:
            logger.error(f"Error reading cache: {e}")
            return None

    def save_recommendation(
        self,
        deal_id: str,
        enriched_data: Dict[str, Any],
        summary: Optional[str],  # Changed to str: expects summary['data_version'] hash
        prompt_template: str,
        company_context: str,
        campaign_context: Optional[str],
        recommendation: Dict[str, Any]
    ):
        """Save recommendation to cache."""
        # Compute hashes
        # Exclude metadata field from enriched_data hash (contains timestamps)
        enriched_data_stable = {k: v for k, v in enriched_data.items() if k != 'metadata'}
        enriched_hash = self._compute_hash(enriched_data_stable)
        summary_hash = summary if summary else None  # summary is already a hash string (data_version)
        prompt_hash = self._compute_hash(prompt_template)
        context_hash = self._compute_hash(company_context)
        campaign_hash = self._compute_hash(campaign_context) if campaign_context else None

        cache_key = self._get_cache_key(deal_id, prompt_hash, context_hash, campaign_hash)

        # Calculate expiration
        generated_at = datetime.now()
        expires_at = generated_at + timedelta(minutes=self.ttl_minutes)

        try:
            with sqlite3.connect(self.cache_file) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO recommendation_cache
                    (cache_key, enriched_data_hash, summary_hash, prompt_hash,
                     company_context_hash, campaign_context_hash,
                     enriched_data_json, summary_json, recommendation_json,
                     generated_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cache_key,
                    enriched_hash,
                    summary_hash,
                    prompt_hash,
                    context_hash,
                    campaign_hash,
                    json.dumps(enriched_data),
                    summary,  # summary is already a hash string, no need to json.dumps
                    json.dumps(recommendation),
                    generated_at.isoformat(),
                    expires_at.isoformat()
                ))
                conn.commit()
                logger.info(f"Saved recommendation to cache: {cache_key}")

        except Exception as e:
            logger.error(f"Error saving to cache: {e}")

    def log_feedback(
        self,
        recommendation_id: str,
        deal_id: str,
        action_priority: str,
        action_channel: str,
        feedback_type: str,
        feedback_text: str,
        what_worked: Optional[str],
        what_didnt_work: Optional[str],
        suggested_improvement: Optional[str]
    ) -> int:
        """
        Log user feedback.

        Returns:
            Feedback ID for linking to context updates
        """
        try:
            with sqlite3.connect(self.cache_file) as conn:
                cursor = conn.execute("""
                    INSERT INTO feedback_log
                    (recommendation_id, deal_id, action_priority, action_channel,
                     feedback_type, feedback_text, what_worked, what_didnt_work,
                     suggested_improvement)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    recommendation_id,
                    deal_id,
                    action_priority,
                    action_channel,
                    feedback_type,
                    feedback_text,
                    what_worked,
                    what_didnt_work,
                    suggested_improvement
                ))
                conn.commit()
                feedback_id = cursor.lastrowid
                logger.info(f"Logged feedback: ID={feedback_id}")
                return feedback_id

        except Exception as e:
            logger.error(f"Error logging feedback: {e}")
            return -1

    def log_context_update(
        self,
        update_type: str,
        section: str,
        content: str,
        source_feedback_id: Optional[int]
    ):
        """Log a context update."""
        try:
            with sqlite3.connect(self.cache_file) as conn:
                conn.execute("""
                    INSERT INTO context_updates
                    (update_type, section, content, source_feedback_id)
                    VALUES (?, ?, ?, ?)
                """, (update_type, section, content, source_feedback_id))
                conn.commit()
                logger.info(f"Logged context update: {update_type} in {section}")

        except Exception as e:
            logger.error(f"Error logging context update: {e}")

    def clear_cache(self, cache_key: Optional[str] = None):
        """Clear cache entries."""
        try:
            with sqlite3.connect(self.cache_file) as conn:
                if cache_key:
                    conn.execute("DELETE FROM recommendation_cache WHERE cache_key = ?", (cache_key,))
                    logger.info(f"Cleared cache for {cache_key}")
                else:
                    conn.execute("DELETE FROM recommendation_cache")
                    logger.info("Cleared all cache")
                conn.commit()

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            with sqlite3.connect(self.cache_file) as conn:
                conn.row_factory = sqlite3.Row

                # Total entries
                cursor = conn.execute("SELECT COUNT(*) as total FROM recommendation_cache")
                total = cursor.fetchone()["total"]

                # Fresh entries (not expired)
                now = datetime.now().isoformat()
                cursor = conn.execute("""
                    SELECT COUNT(*) as fresh
                    FROM recommendation_cache
                    WHERE expires_at > ?
                """, (now,))
                fresh = cursor.fetchone()["fresh"]

                # Total feedback
                cursor = conn.execute("SELECT COUNT(*) as feedback FROM feedback_log")
                feedback_count = cursor.fetchone()["feedback"]

                # Total context updates
                cursor = conn.execute("SELECT COUNT(*) as updates FROM context_updates")
                updates_count = cursor.fetchone()["updates"]

                return {
                    "total_recommendations": total,
                    "fresh_recommendations": fresh,
                    "expired_recommendations": total - fresh,
                    "total_feedback": feedback_count,
                    "total_context_updates": updates_count,
                    "ttl_minutes": self.ttl_minutes
                }

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                "total_recommendations": 0,
                "fresh_recommendations": 0,
                "expired_recommendations": 0,
                "total_feedback": 0,
                "total_context_updates": 0,
                "ttl_minutes": self.ttl_minutes
            }
