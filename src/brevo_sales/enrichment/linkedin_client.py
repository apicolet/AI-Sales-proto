"""
LinkedIn enrichment plugin using Pipedream workflows.
"""
import requests
import logging
from typing import Optional, Dict, Any
from brevo_sales.enrichment.models import LinkedInProfile, LinkedInCompany
from brevo_sales.cache.manager import CacheManager

logger = logging.getLogger(__name__)


class LinkedInClient:
    """
    LinkedIn enrichment client using Pipedream workflows.

    Supports two modes:
    1. Pipedream workflow (recommended) - via custom workflow URL
    2. Direct API (future) - direct LinkedIn API integration
    """

    def __init__(
        self,
        provider: str,
        cache_manager: CacheManager,
        api_key: Optional[str] = None,
        pipedream_workflow_url: Optional[str] = None
    ):
        """
        Initialize LinkedIn client.

        Args:
            provider: "pipedream" or "direct"
            cache_manager: Cache manager instance
            api_key: LinkedIn API key (for direct mode)
            pipedream_workflow_url: Pipedream workflow URL
        """
        self.provider = provider
        self.cache_manager = cache_manager
        self.api_key = api_key
        self.pipedream_workflow_url = pipedream_workflow_url
        self.session = requests.Session()

    def _get_cached_or_fetch(
        self,
        entity_type: str,
        entity_id: str,
        fetch_func: callable
    ) -> Optional[Dict[str, Any]]:
        """Get data from cache or fetch from LinkedIn."""
        # Try cache first (LinkedIn data has 24h TTL)
        cached = self.cache_manager.get("linkedin", entity_type, entity_id)

        if cached:
            logger.info(f"LinkedIn cache HIT: {entity_type}:{entity_id}")
            return cached["data"]

        # Cache miss - fetch from LinkedIn
        logger.info(f"Fetching LinkedIn data for {entity_type}:{entity_id}")

        try:
            data = fetch_func()
            if data:
                # Store in cache with 24h TTL
                self.cache_manager.set("linkedin", entity_type, entity_id, data)
            return data
        except Exception as e:
            logger.error(f"LinkedIn fetch failed: {e}")
            return None

    def get_profile_by_email(self, email: str) -> Optional[LinkedInProfile]:
        """
        Get LinkedIn profile by email address.

        Args:
            email: Email address to search

        Returns:
            LinkedInProfile or None if not found
        """
        def fetch():
            if self.provider == "pipedream":
                return self._fetch_profile_pipedream(email)
            else:
                raise NotImplementedError(f"Provider {self.provider} not yet implemented")

        data = self._get_cached_or_fetch("profile", email, fetch)

        if data:
            try:
                return LinkedInProfile(**data)
            except Exception as e:
                logger.error(f"Failed to parse LinkedIn profile: {e}")
                return None

        return None

    def get_company_profile(
        self,
        company_name: Optional[str] = None,
        company_domain: Optional[str] = None
    ) -> Optional[LinkedInCompany]:
        """
        Get LinkedIn company profile by name or domain.

        Args:
            company_name: Company name
            company_domain: Company domain (e.g., "mericq.fr")

        Returns:
            LinkedInCompany or None if not found
        """
        if not company_name and not company_domain:
            return None

        identifier = company_domain or company_name

        def fetch():
            if self.provider == "pipedream":
                return self._fetch_company_pipedream(company_name, company_domain)
            else:
                raise NotImplementedError(f"Provider {self.provider} not yet implemented")

        data = self._get_cached_or_fetch("company", identifier, fetch)

        if data:
            try:
                return LinkedInCompany(**data)
            except Exception as e:
                logger.error(f"Failed to parse LinkedIn company: {e}")
                return None

        return None

    # ========== Pipedream Integration ==========

    def _fetch_profile_pipedream(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Fetch LinkedIn profile via Pipedream workflow.

        Expected Pipedream workflow:
        - Trigger: HTTP POST request
        - Input: {"email": "user@domain.com"}
        - Output: LinkedIn profile JSON
        """
        if not self.pipedream_workflow_url:
            logger.warning("Pipedream workflow URL not configured")
            return None

        try:
            response = self.session.post(
                self.pipedream_workflow_url,
                json={"action": "get_profile", "email": email},
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Pipedream request failed: {e}")
            return None

    def _fetch_company_pipedream(
        self,
        company_name: Optional[str],
        company_domain: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch LinkedIn company via Pipedream workflow.

        Expected Pipedream workflow:
        - Trigger: HTTP POST request
        - Input: {"company_name": "...", "company_domain": "..."}
        - Output: LinkedIn company JSON
        """
        if not self.pipedream_workflow_url:
            logger.warning("Pipedream workflow URL not configured")
            return None

        try:
            payload = {"action": "get_company"}
            if company_name:
                payload["company_name"] = company_name
            if company_domain:
                payload["company_domain"] = company_domain

            response = self.session.post(
                self.pipedream_workflow_url,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Pipedream request failed: {e}")
            return None
