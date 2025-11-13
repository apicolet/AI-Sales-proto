"""
Brevo API client wrapper with caching support.
"""
import requests
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from brevo_data_gatherer.models.schemas import (
    BrevoContact, BrevoCompany, BrevoDeal, BrevoNote, BrevoTask
)
from brevo_data_gatherer.cache.manager import CacheManager

logger = logging.getLogger(__name__)


class BrevoClient:
    """
    Brevo API client with intelligent caching.

    Handles all communication with Brevo CRM API and manages caching
    with appropriate TTLs per data type.
    """

    def __init__(self, api_key: str, base_url: str, cache_manager: CacheManager):
        """Initialize Brevo client."""
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.cache_manager = cache_manager
        self.session = requests.Session()
        self.session.headers.update({
            'api-key': api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def _get_cached_or_fetch(
        self,
        source: str,
        entity_type: str,
        entity_id: str,
        fetch_func: callable
    ) -> Dict[str, Any]:
        """
        Generic method to get data from cache or fetch from API.

        Args:
            source: Cache source identifier
            entity_type: Entity type (contact, deal, company)
            entity_id: Entity ID
            fetch_func: Function to call if cache miss

        Returns:
            Data from cache or API
        """
        # Try cache first
        cached = self.cache_manager.get(source, entity_type, entity_id)

        if cached:
            return cached["data"]

        # Cache miss - fetch from API
        logger.info(f"Fetching {entity_type} {entity_id} from {source}")
        data = fetch_func()

        # Store in cache
        self.cache_manager.set(source, entity_type, entity_id, data)

        return data

    # ========== Contact Methods ==========

    def get_contact(self, identifier: str, identifier_type: str = "email") -> Optional[BrevoContact]:
        """
        Get contact by email or ID with caching.

        Args:
            identifier: Email address or contact ID
            identifier_type: "email" or "contact_id"
        """
        def fetch():
            url = f"{self.base_url}/contacts/{identifier}"
            params = {}
            if identifier_type != "email":
                params["identifierType"] = identifier_type

            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()

        data = self._get_cached_or_fetch(
            "brevo_crm",
            "contact",
            identifier,
            fetch
        )

        return BrevoContact(**data) if data else None

    def get_contacts_by_company(self, company_id: str) -> List[BrevoContact]:
        """
        Get all contacts linked to a company.

        Note: This fetches individual contacts based on company.linkedContactsIds
        since Brevo API doesn't have a direct contacts filter by company.

        Args:
            company_id: The company ID to filter by

        Returns:
            List of BrevoContact objects
        """
        # First get the company to access its linkedContactsIds
        company = self.get_company(company_id)
        if not company:
            logger.warning(f"Company {company_id} not found")
            return []

        # Get linked contact IDs
        linked_ids = getattr(company, 'linkedContactsIds', [])
        if not linked_ids:
            logger.debug(f"No linked contacts for company {company_id}")
            return []

        # Fetch each contact (these will be cached individually)
        contacts = []
        for contact_id in linked_ids:
            try:
                contact = self.get_contact(str(contact_id), "contact_id")
                if contact:
                    contacts.append(contact)
            except Exception as e:
                logger.warning(f"Error fetching contact {contact_id} for company {company_id}: {e}")

        return contacts

    # ========== Company Methods ==========

    def get_company(self, company_id: str) -> Optional[BrevoCompany]:
        """Get company by ID with caching."""
        def fetch():
            url = f"{self.base_url}/companies/{company_id}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()

        data = self._get_cached_or_fetch(
            "brevo_crm",
            "company",
            company_id,
            fetch
        )

        return BrevoCompany(**data) if data else None

    def get_companies_by_contact(self, contact_id: int) -> List[BrevoCompany]:
        """
        Get all companies linked to a contact with caching.

        Args:
            contact_id: The contact ID to filter by

        Returns:
            List of BrevoCompany objects
        """
        cache_key = f"contact_{contact_id}_companies"

        def fetch():
            url = f"{self.base_url}/companies"
            params = {"linkedContactsIds": contact_id, "limit": 100}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()

        data = self._get_cached_or_fetch(
            "brevo_crm",
            "companies_list",
            cache_key,
            fetch
        )

        # Parse companies
        companies_list = data.get("items", []) if isinstance(data, dict) else data
        return [BrevoCompany(**company) for company in companies_list]

    # ========== Deal Methods ==========

    def get_deal(self, deal_id: str) -> Optional[BrevoDeal]:
        """Get deal by ID with caching."""
        def fetch():
            url = f"{self.base_url}/crm/deals/{deal_id}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()

        data = self._get_cached_or_fetch(
            "brevo_crm",
            "deal",
            deal_id,
            fetch
        )

        return BrevoDeal(**data) if data else None

    def get_deals_by_contact(self, contact_id: int) -> List[BrevoDeal]:
        """
        Get all deals linked to a contact with caching.

        Args:
            contact_id: The contact ID to filter by

        Returns:
            List of BrevoDeal objects
        """
        cache_key = f"contact_{contact_id}_deals"

        def fetch():
            url = f"{self.base_url}/crm/deals"
            params = {"filters[linkedContactsIds]": str(contact_id), "limit": 100}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()

        data = self._get_cached_or_fetch(
            "brevo_crm",
            "deals_list",
            cache_key,
            fetch
        )

        # Parse deals
        deals_list = data.get("items", []) if isinstance(data, dict) else data
        return [BrevoDeal(**deal) for deal in deals_list]

    def get_all_pipelines(self) -> Dict[str, Any]:
        """
        Get all pipelines with their stages. Cached globally since pipelines rarely change.

        Returns a dict mapping pipeline_id -> {name, stages: {stage_id -> stage_name}}
        """
        def fetch():
            url = f"{self.base_url}/crm/pipeline/details/all"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()

        # Use a global cache key for all pipelines (same for everyone)
        data = self._get_cached_or_fetch(
            "brevo_crm",
            "pipelines",
            "all",
            fetch
        )

        # Transform to easier-to-use format: {pipeline_id: {name: ..., stages: {stage_id: stage_name}}}
        pipelines_map = {}
        if isinstance(data, list):
            for pipeline in data:
                # API returns "pipeline" not "pipeline_id"
                pipeline_id = pipeline.get("pipeline") or pipeline.get("pipeline_id")
                # API returns "pipeline_name" not "name"
                pipeline_name = pipeline.get("pipeline_name") or pipeline.get("name", "Unknown Pipeline")
                stages = {}
                for stage in pipeline.get("stages", []):
                    stage_id = stage.get("id")
                    stage_name = stage.get("name")
                    if stage_id:
                        stages[stage_id] = stage_name

                if pipeline_id:
                    pipelines_map[pipeline_id] = {
                        "name": pipeline_name,
                        "stages": stages
                    }

        return pipelines_map

    # ========== Users Methods ==========

    def get_invited_users(self) -> List[Dict[str, Any]]:
        """
        Get all invited users in the organization. Cached globally since users don't change often.

        Returns:
            List of users with id, email, status, feature_access
        """
        def fetch():
            url = f"{self.base_url}/organization/invited/users"
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("users", [])

        # Use a global cache key for all users (same for everyone)
        users = self._get_cached_or_fetch(
            "brevo_users",
            "users",
            "all",
            fetch
        )

        return users

    # ========== Notes Methods ==========

    def get_notes(
        self,
        entity_type: str,
        entity_ids: List[str],
        date_from: Optional[int] = None,
        date_to: Optional[int] = None
    ) -> List[BrevoNote]:
        """
        Get notes for contacts/companies/deals with caching.

        Args:
            entity_type: "contacts", "companies", or "deals"
            entity_ids: List of entity IDs
            date_from: Start date in Unix timestamp (milliseconds)
            date_to: End date in Unix timestamp (milliseconds)
        """
        # Use combined entity_ids as cache key
        cache_key = f"{entity_type}:{'_'.join(entity_ids)}"

        def fetch():
            url = f"{self.base_url}/crm/notes"
            params = {
                "entity": entity_type,
                "entityIds": ','.join(entity_ids)
            }
            if date_from:
                params["dateFrom"] = date_from
            if date_to:
                params["dateTo"] = date_to

            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()

        data = self._get_cached_or_fetch(
            "brevo_notes",
            entity_type,
            cache_key,
            fetch
        )

        # Parse notes
        notes_list = data.get("results", []) if isinstance(data, dict) else data
        return [BrevoNote(**note) for note in notes_list]

    # ========== Tasks Methods ==========

    def get_tasks(
        self,
        filter_type: Optional[str] = None,
        filter_status: Optional[str] = None,
        filter_date: Optional[str] = None,
        filter_assign_to: Optional[str] = None,
        filter_contacts: Optional[List[str]] = None,
        filter_deals: Optional[List[str]] = None,
        filter_companies: Optional[List[str]] = None
    ) -> List[BrevoTask]:
        """
        Get tasks with various filters and caching.

        Args:
            filter_type: Task type ID
            filter_status: "done" or "undone"
            filter_date: Date filter ("overdue", "today", "tomorrow", "week")
            filter_assign_to: Email address of assigned user
            filter_contacts: List of contact IDs
            filter_deals: List of deal IDs
            filter_companies: List of company IDs
        """
        # Build cache key from filters
        cache_parts = []
        if filter_contacts:
            cache_parts.append(f"contacts:{'_'.join(filter_contacts)}")
        if filter_deals:
            cache_parts.append(f"deals:{'_'.join(filter_deals)}")
        if filter_companies:
            cache_parts.append(f"companies:{'_'.join(filter_companies)}")

        cache_key = "_".join(cache_parts) if cache_parts else "all"

        def fetch():
            url = f"{self.base_url}/crm/tasks"
            params = {}
            if filter_type:
                params["filter[type]"] = filter_type
            if filter_status:
                params["filter[status]"] = filter_status
            if filter_date:
                params["filter[date]"] = filter_date
            if filter_assign_to:
                params["filter[assignTo]"] = filter_assign_to
            if filter_contacts:
                params["filter[contacts]"] = ','.join(filter_contacts) if isinstance(filter_contacts, list) else filter_contacts
            if filter_deals:
                params["filter[deals]"] = ','.join(filter_deals) if isinstance(filter_deals, list) else filter_deals
            if filter_companies:
                params["filter[companies]"] = ','.join(filter_companies) if isinstance(filter_companies, list) else filter_companies

            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()

        data = self._get_cached_or_fetch(
            "brevo_tasks",
            "tasks",
            cache_key,
            fetch
        )

        # Parse tasks
        tasks_list = data.get("items", []) if isinstance(data, dict) else data
        return [BrevoTask(**task) for task in tasks_list]

    # ========== Helper Methods ==========

    def get_all_related_data(
        self,
        entity_type: str,
        entity_id: str
    ) -> Dict[str, Any]:
        """
        Get all related data for an entity (entity + notes + tasks).

        Args:
            entity_type: "contact", "deal", or "company"
            entity_id: Entity ID

        Returns:
            Dictionary with entity, notes, and tasks
        """
        result = {
            "entity": None,
            "notes": [],
            "tasks": []
        }

        # Get primary entity
        if entity_type == "contact":
            result["entity"] = self.get_contact(entity_id)
        elif entity_type == "deal":
            result["entity"] = self.get_deal(entity_id)
        elif entity_type == "company":
            result["entity"] = self.get_company(entity_id)

        if not result["entity"]:
            return result

        # Get notes
        try:
            if entity_type == "contact":
                result["notes"] = self.get_notes("contacts", [entity_id])
            elif entity_type == "deal":
                result["notes"] = self.get_notes("deals", [entity_id])
            elif entity_type == "company":
                result["notes"] = self.get_notes("companies", [entity_id])
        except Exception as e:
            logger.warning(f"Failed to fetch notes for {entity_type} {entity_id}: {e}")

        # Get tasks
        try:
            filter_kwargs = {}
            if entity_type == "contact":
                filter_kwargs["filter_contacts"] = [entity_id]
            elif entity_type == "deal":
                filter_kwargs["filter_deals"] = [entity_id]
            elif entity_type == "company":
                filter_kwargs["filter_companies"] = [entity_id]

            result["tasks"] = self.get_tasks(**filter_kwargs)
        except Exception as e:
            logger.warning(f"Failed to fetch tasks for {entity_type} {entity_id}: {e}")

        return result
