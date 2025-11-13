"""
Web search plugin for company intelligence.
"""
import requests
import logging
from typing import List, Optional, Dict, Any
from brevo_data_gatherer.models.schemas import WebSearchResult, CompanyIntelligence
from brevo_data_gatherer.cache.manager import CacheManager

logger = logging.getLogger(__name__)


class WebSearchClient:
    """
    Web search client for company intelligence gathering.

    Supports:
    - Serper API (recommended) - https://serper.dev
    - Google Custom Search API (future)
    """

    def __init__(
        self,
        provider: str,
        cache_manager: CacheManager,
        api_key: Optional[str] = None
    ):
        """
        Initialize web search client.

        Args:
            provider: "serper" or "google"
            cache_manager: Cache manager instance
            api_key: API key for the search provider
        """
        self.provider = provider
        self.cache_manager = cache_manager
        self.api_key = api_key
        self.session = requests.Session()

        if provider == "serper":
            self.session.headers.update({
                'X-API-KEY': api_key,
                'Content-Type': 'application/json'
            })

    def _get_cached_or_search(
        self,
        query: str,
        search_func: callable
    ) -> List[WebSearchResult]:
        """Get search results from cache or perform search."""
        # Use query as cache key
        cache_key = f"search:{query}"

        # Try cache first (24h TTL)
        cached = self.cache_manager.get("web_search", "search", cache_key)

        if cached:
            logger.info(f"Web search cache HIT: {query}")
            results = cached["data"]
            return [WebSearchResult(**r) for r in results]

        # Cache miss - perform search
        logger.info(f"Performing web search: {query}")

        try:
            results = search_func()
            if results:
                # Store in cache with 24h TTL
                results_data = [r.dict() for r in results]
                self.cache_manager.set("web_search", "search", cache_key, results_data)
            return results

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []

    def search_company(
        self,
        company_name: str,
        additional_terms: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[WebSearchResult]:
        """
        Search for company information.

        Args:
            company_name: Company name to search
            additional_terms: Additional search terms (e.g., ["acquisition", "news"])
            max_results: Maximum number of results

        Returns:
            List of search results
        """
        query = company_name
        if additional_terms:
            query += " " + " ".join(additional_terms)

        def search():
            if self.provider == "serper":
                return self._search_serper(query, max_results)
            elif self.provider == "google":
                return self._search_google(query, max_results)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")

        return self._get_cached_or_search(query, search)

    def gather_company_intelligence(
        self,
        company_name: str,
        company_domain: Optional[str] = None
    ) -> CompanyIntelligence:
        """
        Gather comprehensive company intelligence from multiple searches.

        Args:
            company_name: Company name
            company_domain: Company domain for tech stack detection

        Returns:
            CompanyIntelligence with key facts, tech stack, and recent news
        """
        intelligence = CompanyIntelligence()

        # Search 1: General company information
        general_results = self.search_company(company_name, max_results=5)
        for result in general_results:
            intelligence.key_facts.append(f"{result.title}: {result.snippet}")

        # Search 2: Recent news and acquisitions
        news_results = self.search_company(
            company_name,
            additional_terms=["news", "acquisition", "expansion"],
            max_results=3
        )
        for result in news_results:
            intelligence.recent_news.append({
                "title": result.title,
                "url": result.url,
                "snippet": result.snippet,
                "date": result.date
            })

        # Search 3: Tech stack (if domain provided)
        if company_domain:
            tech_results = self.search_company(
                company_domain,
                additional_terms=["technology", "tools", "software"],
                max_results=3
            )
            # Parse tech stack from results (basic extraction)
            for result in tech_results:
                # This is a simple extraction - could be improved with NLP
                if any(keyword in result.snippet.lower() for keyword in ["mailchimp", "salesforce", "hubspot", "marketo"]):
                    intelligence.tech_stack.append({
                        "tool": "Unknown",  # Would need better extraction
                        "category": "Marketing/CRM",
                        "verified": False,
                        "source": result.url
                    })

        return intelligence

    # ========== Serper API Integration ==========

    def _search_serper(self, query: str, max_results: int) -> List[WebSearchResult]:
        """
        Perform search using Serper API.

        API docs: https://serper.dev/docs
        """
        if not self.api_key:
            logger.warning("Serper API key not configured")
            return []

        try:
            response = self.session.post(
                'https://google.serper.dev/search',
                json={
                    "q": query,
                    "num": max_results
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("organic", [])[:max_results]:
                results.append(WebSearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    date=item.get("date"),
                    relevanceScore=item.get("position", 0)
                ))

            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"Serper API request failed: {e}")
            return []

    # ========== Google Custom Search Integration ==========

    def _search_google(self, query: str, max_results: int) -> List[WebSearchResult]:
        """
        Perform search using Google Custom Search API.

        API docs: https://developers.google.com/custom-search/v1/overview
        """
        # Placeholder for future implementation
        raise NotImplementedError("Google Custom Search not yet implemented")
