"""
Main enrichment orchestrator.

Coordinates all data gathering from multiple sources and builds
the complete enriched data structure.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import time

from brevo_data_gatherer.models.schemas import EnrichedData
from brevo_data_gatherer.core.brevo_client import BrevoClient
from brevo_data_gatherer.core.linkedin_client import LinkedInClient
from brevo_data_gatherer.core.web_client import WebSearchClient
from brevo_data_gatherer.core.conversations_client import ConversationsClient
from brevo_data_gatherer.cache.manager import CacheManager

logger = logging.getLogger(__name__)


class DataEnricher:
    """
    Main orchestrator for data enrichment.

    Phases:
    1. Identify entity (contact/deal/company) and fetch from Brevo
    2. Fetch related entities (contacts linked to deals, companies linked to contacts, etc.)
    3. Gather interaction history (notes, tasks)
    4. Enrich with LinkedIn profiles
    5. Gather company intelligence via web search
    6. Build final enriched data structure
    """

    def __init__(
        self,
        brevo_client: BrevoClient,
        linkedin_client: Optional[LinkedInClient] = None,
        web_client: Optional[WebSearchClient] = None,
        conversations_client: Optional[ConversationsClient] = None,
        cache_manager: Optional[CacheManager] = None
    ):
        """Initialize enricher with API clients."""
        self.brevo_client = brevo_client
        self.linkedin_client = linkedin_client
        self.web_client = web_client
        self.conversations_client = conversations_client
        self.cache_manager = cache_manager

        # Fetch pipelines once for stage name lookups (cached globally)
        try:
            self.pipelines = self.brevo_client.get_all_pipelines()
            logger.info(f"Loaded {len(self.pipelines)} pipelines with stage definitions")
        except Exception as e:
            logger.warning(f"Could not load pipelines: {e}. Stage names will not be resolved.")
            self.pipelines = {}

        # Statistics
        self.stats = {
            "api_calls_made": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "sources_used": []
        }

    def enrich(
        self,
        entity_identifier: str,
        entity_type: str = "auto",
        identifier_type: str = "auto"
    ) -> EnrichedData:
        """
        Main enrichment method.

        Args:
            entity_identifier: Email, contact ID, deal ID, or company ID
            entity_type: "contact", "deal", "company", or "auto" to detect
            identifier_type: "email", "contact_id", "deal_id", "company_id", or "auto"

        Returns:
            Complete enriched data structure
        """
        start_time = time.time()

        # Reset stats
        self.stats = {
            "api_calls_made": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "sources_used": ["brevo_crm"]
        }

        # Auto-detect entity type if needed
        if entity_type == "auto":
            entity_type, identifier_type = self._detect_entity_type(entity_identifier, identifier_type)

        logger.info(f"Starting enrichment for {entity_type}: {entity_identifier}")

        # Phase 1: Fetch primary entity
        primary_record = self._fetch_primary_entity(entity_type, entity_identifier, identifier_type)

        if not primary_record:
            raise ValueError(f"Could not fetch {entity_type} with identifier: {entity_identifier}")

        # Phase 2: Fetch related entities
        related_entities = self._fetch_related_entities(entity_type, primary_record)

        # Phase 3: Gather interaction history
        interaction_history = self._gather_interaction_history(entity_type, primary_record, related_entities)

        # Phase 3.5: For contacts, fetch related deals/companies from notes and tasks
        if entity_type == "contact":
            self._fetch_related_from_interactions(interaction_history, related_entities)

        # Phase 4 & 5: Enrich with LinkedIn and web search
        enrichment_data = self._gather_enrichment(primary_record, related_entities)

        # Resolve stage IDs to stage names for all deals
        primary_record_dict = primary_record.dict() if hasattr(primary_record, 'dict') else primary_record
        if entity_type == "deal":
            primary_record_dict = self._resolve_deal_stage_names(primary_record_dict)

        # Resolve stage names for deals in related entities
        if "deals" in related_entities:
            related_entities["deals"] = [
                self._resolve_deal_stage_names(deal.dict() if hasattr(deal, 'dict') else deal)
                for deal in related_entities["deals"]
            ]

        # Resolve deal owner info
        deal_owner_info = None
        if entity_type == "deal":
            deal_owner_info = self._resolve_deal_owner(primary_record_dict)

        # Build final structure
        enriched_data = EnrichedData(
            primary_type=entity_type,
            primary_record=primary_record_dict,
            related_entities=related_entities,
            interaction_history=interaction_history,
            enrichment=enrichment_data,
            metadata={
                "enrichment_timestamp": datetime.now().isoformat(),
                "api_calls_made": self.stats["api_calls_made"],
                "data_quality": self._assess_data_quality(related_entities, enrichment_data),
                "sources_used": self.stats["sources_used"],
                "cache_hit_rate": self._calculate_cache_hit_rate(),
                "duration_ms": int((time.time() - start_time) * 1000),
                "deal_owner": deal_owner_info  # Add owner info to metadata
            }
        )

        # Log enrichment run
        if self.cache_manager:
            self.cache_manager.log_enrichment_run(
                entity_id=entity_identifier,
                entity_type=entity_type,
                sources_used=self.stats["sources_used"],
                cache_hits=self.stats["cache_hits"],
                cache_misses=self.stats["cache_misses"],
                api_calls_made=self.stats["api_calls_made"],
                duration_ms=enriched_data.metadata["duration_ms"],
                success=True
            )

        logger.info(f"Enrichment complete: {self.stats['api_calls_made']} API calls, "
                   f"{enriched_data.metadata['duration_ms']}ms")

        return enriched_data

    def _detect_entity_type(
        self,
        entity_identifier: str,
        identifier_type: str
    ) -> tuple[str, str]:
        """Auto-detect entity type from identifier."""
        # Email format
        if "@" in entity_identifier:
            return "contact", "email"

        # MongoDB ObjectID format (24 hex chars) - typically company/deal IDs
        if len(entity_identifier) == 24 and all(c in "0123456789abcdefABCDEF" for c in entity_identifier):
            # Try to detect from identifier_type hint or default to deal
            if identifier_type == "company_id":
                return "company", "company_id"
            else:
                return "deal", "deal_id"

        # Numeric ID - likely contact ID
        if entity_identifier.isdigit():
            return "contact", "contact_id"

        # Default to contact with email
        return "contact", "email"

    def _fetch_primary_entity(
        self,
        entity_type: str,
        entity_identifier: str,
        identifier_type: str
    ) -> Any:
        """Fetch the primary entity from Brevo."""
        self.stats["api_calls_made"] += 1

        if entity_type == "contact":
            return self.brevo_client.get_contact(entity_identifier, identifier_type)
        elif entity_type == "deal":
            return self.brevo_client.get_deal(entity_identifier)
        elif entity_type == "company":
            return self.brevo_client.get_company(entity_identifier)
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")

    def _fetch_related_entities(
        self,
        primary_type: str,
        primary_record: Any
    ) -> Dict[str, List[Any]]:
        """Fetch all related entities."""
        related = {
            "contacts": [],
            "companies": [],
            "deals": []
        }

        try:
            if primary_type == "contact":
                # Contact is primary - no related contacts
                related["contacts"] = [primary_record]

                # For contacts, we'll fetch related deals and companies from notes/tasks
                # This will be populated after gathering interaction history
                pass

            elif primary_type == "deal":
                # Deal is primary
                related["deals"] = [primary_record]

                # Track unique IDs to avoid duplicates
                contact_ids_seen = set()
                company_ids_seen = set()

                # Step 1: Fetch linked contacts from the deal
                if hasattr(primary_record, 'linkedContactsIds'):
                    for contact_id in primary_record.linkedContactsIds:
                        if contact_id not in contact_ids_seen:
                            contact = self.brevo_client.get_contact(str(contact_id), "contact_id")
                            if contact:
                                related["contacts"].append(contact)
                                contact_ids_seen.add(contact_id)
                                self.stats["api_calls_made"] += 1

                # Step 2: Fetch linked companies from the deal
                if hasattr(primary_record, 'linkedCompaniesIds'):
                    for company_id in primary_record.linkedCompaniesIds:
                        if company_id not in company_ids_seen:
                            company = self.brevo_client.get_company(company_id)
                            if company:
                                related["companies"].append(company)
                                company_ids_seen.add(company_id)
                                self.stats["api_calls_made"] += 1

                # Step 3: For each contact, fetch their companies (if different from deal companies)
                logger.info(f"Fetching companies for {len(related['contacts'])} contacts")
                for contact in related["contacts"]:
                    contact_id = contact.id if hasattr(contact, 'id') else contact.get('id')
                    try:
                        contact_companies = self.brevo_client.get_companies_by_contact(contact_id)
                        for company in contact_companies:
                            company_id = company.id if hasattr(company, 'id') else company.get('id')
                            if company_id not in company_ids_seen:
                                related["companies"].append(company)
                                company_ids_seen.add(company_id)
                                logger.debug(f"Added company {company_id} from contact {contact_id}")
                        self.stats["api_calls_made"] += 1
                    except Exception as e:
                        logger.warning(f"Error fetching companies for contact {contact_id}: {e}")

                # Step 4: For each company, fetch all OTHER contacts in that company
                logger.info(f"Fetching contacts for {len(related['companies'])} companies")
                for company in related["companies"]:
                    company_id = company.id if hasattr(company, 'id') else company.get('id')
                    try:
                        company_contacts = self.brevo_client.get_contacts_by_company(company_id)
                        for contact in company_contacts:
                            contact_id = contact.id if hasattr(contact, 'id') else contact.get('id')
                            if contact_id not in contact_ids_seen:
                                related["contacts"].append(contact)
                                contact_ids_seen.add(contact_id)
                                logger.debug(f"Added contact {contact_id} from company {company_id}")
                        self.stats["api_calls_made"] += 1
                    except Exception as e:
                        logger.warning(f"Error fetching contacts for company {company_id}: {e}")

            elif primary_type == "company":
                # Fetch linked contacts
                if hasattr(primary_record, 'linkedContactsIds'):
                    for contact_id in primary_record.linkedContactsIds:
                        contact = self.brevo_client.get_contact(str(contact_id), "contact_id")
                        if contact:
                            related["contacts"].append(contact)
                            self.stats["api_calls_made"] += 1

                # Fetch linked deals
                if hasattr(primary_record, 'linkedDealsIds'):
                    for deal_id in primary_record.linkedDealsIds:
                        deal = self.brevo_client.get_deal(deal_id)
                        if deal:
                            related["deals"].append(deal)
                            self.stats["api_calls_made"] += 1

                # Company is primary
                related["companies"] = [primary_record]

        except Exception as e:
            logger.warning(f"Error fetching related entities: {e}")

        return related

    def _fetch_related_from_interactions(
        self,
        interaction_history: Dict[str, List[Any]],
        related_entities: Dict[str, List[Any]]
    ):
        """
        Fetch related deals and companies using efficient API filters.

        For contacts, we query the Brevo API directly with linkedContactsIds filter
        instead of extracting IDs from notes/tasks.
        """
        try:
            # Get the contact ID from the primary contact
            primary_contact = related_entities.get("contacts", [])[0] if related_entities.get("contacts") else None
            if not primary_contact:
                logger.warning("No primary contact found, skipping related entities fetch")
                return

            # Extract contact ID (handle both dict and Pydantic model)
            if hasattr(primary_contact, 'id'):
                contact_id = primary_contact.id
            elif isinstance(primary_contact, dict):
                contact_id = primary_contact.get('id')
            else:
                logger.warning("Could not extract contact ID")
                return

            logger.info(f"Fetching related entities for contact ID: {contact_id}")

            # Fetch all deals linked to this contact (1 API call)
            try:
                deals = self.brevo_client.get_deals_by_contact(contact_id)
                related_entities["deals"].extend(deals)
                self.stats["api_calls_made"] += 1
                logger.info(f"Fetched {len(deals)} deals for contact {contact_id}")
            except Exception as e:
                logger.warning(f"Error fetching deals for contact {contact_id}: {e}")

            # Fetch all companies linked to this contact (1 API call)
            try:
                companies = self.brevo_client.get_companies_by_contact(contact_id)
                related_entities["companies"].extend(companies)
                self.stats["api_calls_made"] += 1
                logger.info(f"Fetched {len(companies)} companies for contact {contact_id}")
            except Exception as e:
                logger.warning(f"Error fetching companies for contact {contact_id}: {e}")

        except Exception as e:
            logger.warning(f"Error fetching related entities: {e}")

    def _gather_interaction_history(
        self,
        primary_type: str,
        primary_record: Any,
        related_entities: Dict[str, List[Any]]
    ) -> Dict[str, List[Any]]:
        """
        Gather interaction history (notes, tasks, conversations) for the PRIMARY entity.

        For deals/companies: Fetch notes/tasks/conversations directly linked to the primary entity
        For contacts: Fetch notes/tasks for the contact and related entities, and conversations from related deals
        """
        history = {
            "notes": [],
            "tasks": [],
            "call_summaries": [],  # Placeholder for future
            "conversations": []
        }

        try:
            # Collect entity IDs
            contact_ids = [str(c.id) for c in related_entities.get("contacts", [])]
            company_ids = [str(c.id) for c in related_entities.get("companies", [])]
            deal_ids = [str(d.id) for d in related_entities.get("deals", [])]

            # Strategy depends on primary type
            if primary_type == "deal":
                # For deals: Only fetch notes/tasks for the PRIMARY deal
                # This avoids getting notes from other deals involving the same contacts/companies
                primary_deal_id = str(primary_record.id) if hasattr(primary_record, 'id') else str(primary_record.get('id'))

                # Fetch notes for primary deal only
                notes = self.brevo_client.get_notes("deals", [primary_deal_id])
                history["notes"].extend(notes)
                self.stats["api_calls_made"] += 1

                # Fetch tasks for primary deal only
                tasks = self.brevo_client.get_tasks(filter_deals=[primary_deal_id])
                history["tasks"].extend(tasks)
                self.stats["api_calls_made"] += 1

            elif primary_type == "company":
                # For companies: Only fetch notes/tasks for the PRIMARY company
                primary_company_id = str(primary_record.id) if hasattr(primary_record, 'id') else str(primary_record.get('id'))

                # Fetch notes for primary company only
                notes = self.brevo_client.get_notes("companies", [primary_company_id])
                history["notes"].extend(notes)
                self.stats["api_calls_made"] += 1

                # Fetch tasks for primary company only
                tasks = self.brevo_client.get_tasks(filter_companies=[primary_company_id])
                history["tasks"].extend(tasks)
                self.stats["api_calls_made"] += 1

            else:  # contact
                # For contacts: Fetch from all related entities to get full context
                if contact_ids:
                    notes = self.brevo_client.get_notes("contacts", contact_ids)
                    history["notes"].extend(notes)
                    self.stats["api_calls_made"] += 1

                if deal_ids:
                    notes = self.brevo_client.get_notes("deals", deal_ids)
                    history["notes"].extend(notes)
                    self.stats["api_calls_made"] += 1

                if company_ids:
                    notes = self.brevo_client.get_notes("companies", company_ids)
                    history["notes"].extend(notes)
                    self.stats["api_calls_made"] += 1

                # Fetch tasks for all related entities
                tasks = self.brevo_client.get_tasks(
                    filter_contacts=contact_ids if contact_ids else None,
                    filter_deals=deal_ids if deal_ids else None,
                    filter_companies=company_ids if company_ids else None
                )
                history["tasks"].extend(tasks)
                self.stats["api_calls_made"] += 1

            # Deduplicate notes and tasks by ID
            history["notes"] = self._deduplicate_by_id(history["notes"])
            history["tasks"] = self._deduplicate_by_id(history["tasks"])

            # Fetch conversations (deal-specific, using cookie-based API)
            if self.conversations_client:
                if primary_type == "deal":
                    # For deals: Fetch conversations for the primary deal
                    primary_deal_id = str(primary_record.id) if hasattr(primary_record, 'id') else str(primary_record.get('id'))
                    try:
                        conversations = self.conversations_client.get_deal_conversations(primary_deal_id)
                        # Convert to dict for JSON serialization
                        history["conversations"].extend([c.dict() for c in conversations])
                        self.stats["api_calls_made"] += 1
                        self.stats["sources_used"].append("brevo_conversations")
                        logger.info(f"Fetched {len(conversations)} conversations for deal {primary_deal_id}")
                    except Exception as e:
                        logger.warning(f"Error fetching conversations for deal {primary_deal_id}: {e}")

                elif primary_type == "contact" and deal_ids:
                    # For contacts: Fetch conversations from related deals
                    for deal_id in deal_ids:
                        try:
                            conversations = self.conversations_client.get_deal_conversations(deal_id)
                            history["conversations"].extend([c.dict() for c in conversations])
                            self.stats["api_calls_made"] += 1
                            if "brevo_conversations" not in self.stats["sources_used"]:
                                self.stats["sources_used"].append("brevo_conversations")
                        except Exception as e:
                            logger.warning(f"Error fetching conversations for deal {deal_id}: {e}")

                elif primary_type == "company" and deal_ids:
                    # For companies: Fetch conversations from related deals
                    for deal_id in deal_ids:
                        try:
                            conversations = self.conversations_client.get_deal_conversations(deal_id)
                            history["conversations"].extend([c.dict() for c in conversations])
                            self.stats["api_calls_made"] += 1
                            if "brevo_conversations" not in self.stats["sources_used"]:
                                self.stats["sources_used"].append("brevo_conversations")
                        except Exception as e:
                            logger.warning(f"Error fetching conversations for deal {deal_id}: {e}")

        except Exception as e:
            logger.warning(f"Error gathering interaction history: {e}")

        return history

    def _deduplicate_by_id(self, items: List[Any]) -> List[Any]:
        """Remove duplicate items based on ID field."""
        seen_ids = set()
        unique_items = []
        for item in items:
            item_id = item.id if hasattr(item, 'id') else item.get('id')
            if item_id and item_id not in seen_ids:
                seen_ids.add(item_id)
                unique_items.append(item)
        return unique_items

    def _gather_enrichment(
        self,
        primary_record: Any,
        related_entities: Dict[str, List[Any]]
    ) -> Dict[str, Any]:
        """Gather enrichment data from LinkedIn and web search."""
        enrichment = {
            "linkedin_profiles": {"contacts": [], "company": None},
            "company_intelligence": None,
            "web_research": []
        }

        # LinkedIn enrichment
        if self.linkedin_client:
            self.stats["sources_used"].append("linkedin")

            # Enrich contacts
            for contact in related_entities.get("contacts", []):
                if hasattr(contact, 'email') and contact.email:
                    profile = self.linkedin_client.get_profile_by_email(contact.email)
                    if profile:
                        enrichment["linkedin_profiles"]["contacts"].append(profile.dict())
                        self.stats["api_calls_made"] += 1

            # Enrich company
            for company in related_entities.get("companies", []):
                if hasattr(company, 'attributes'):
                    company_name = company.attributes.get("name")
                    company_domain = company.attributes.get("website", "").replace("https://", "").replace("http://", "").split("/")[0]

                    if company_name or company_domain:
                        company_profile = self.linkedin_client.get_company_profile(company_name, company_domain)
                        if company_profile:
                            enrichment["linkedin_profiles"]["company"] = company_profile.dict()
                            self.stats["api_calls_made"] += 1
                            break  # Only first company

        # Web search enrichment
        if self.web_client:
            self.stats["sources_used"].append("web_search")

            for company in related_entities.get("companies", []):
                if hasattr(company, 'attributes'):
                    company_name = company.attributes.get("name")
                    company_domain = company.attributes.get("website", "").replace("https://", "").replace("http://", "").split("/")[0]

                    if company_name:
                        intelligence = self.web_client.gather_company_intelligence(company_name, company_domain)
                        enrichment["company_intelligence"] = intelligence.dict()
                        self.stats["api_calls_made"] += 3  # Approximate
                        break  # Only first company

        return enrichment

    def _assess_data_quality(
        self,
        related_entities: Dict[str, List[Any]],
        enrichment_data: Dict[str, Any]
    ) -> str:
        """Assess quality of enriched data."""
        score = 0

        # Base score for related entities
        if related_entities.get("contacts"):
            score += 1
        if related_entities.get("companies"):
            score += 1
        if related_entities.get("deals"):
            score += 1

        # Score for LinkedIn enrichment
        if enrichment_data["linkedin_profiles"]["contacts"]:
            score += 2
        if enrichment_data["linkedin_profiles"]["company"]:
            score += 2

        # Score for company intelligence
        if enrichment_data["company_intelligence"]:
            score += 2

        if score >= 7:
            return "high"
        elif score >= 4:
            return "medium"
        else:
            return "low"

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.stats["cache_hits"] + self.stats["cache_misses"]
        if total == 0:
            return 0.0
        return self.stats["cache_hits"] / total

    def _resolve_deal_stage_names(self, deal_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve stage ID to human-readable stage name for a deal.

        Args:
            deal_dict: Deal data as dictionary

        Returns:
            Deal dict with resolved stage name in attributes
        """
        if not deal_dict or "attributes" not in deal_dict:
            return deal_dict

        attributes = deal_dict["attributes"]
        pipeline_id = attributes.get("deal_pipeline")
        stage_id = attributes.get("deal_stage")

        if not stage_id or not self.pipelines:
            return deal_dict

        # If pipeline_id is specified, look in that pipeline only
        if pipeline_id:
            pipeline = self.pipelines.get(pipeline_id)
            if pipeline:
                stages = pipeline.get("stages", {})
                stage_name = stages.get(stage_id)

                if stage_name:
                    attributes["deal_stage_name"] = stage_name
                    attributes["deal_pipeline_name"] = pipeline.get("name")
                    logger.debug(f"Resolved stage {stage_id} to '{stage_name}' in pipeline '{pipeline.get('name')}'")
                else:
                    attributes["deal_stage_name"] = f"Unknown Stage ({stage_id})"
                    logger.warning(f"Stage ID {stage_id} not found in pipeline {pipeline_id}")
            else:
                attributes["deal_stage_name"] = f"Unknown Pipeline ({pipeline_id})"
                logger.warning(f"Pipeline ID {pipeline_id} not found")
        else:
            # No pipeline ID - search across all pipelines for this stage
            logger.debug(f"No pipeline ID for deal, searching all pipelines for stage {stage_id}")

            for p_id, pipeline_data in self.pipelines.items():
                stages = pipeline_data.get("stages", {})
                if stage_id in stages:
                    stage_name = stages[stage_id]
                    pipeline_name = pipeline_data.get("name")
                    attributes["deal_stage_name"] = stage_name
                    attributes["deal_pipeline_name"] = pipeline_name
                    attributes["deal_pipeline"] = p_id  # Set the pipeline ID for future reference
                    logger.info(f"Resolved stage {stage_id} to '{stage_name}' in pipeline '{pipeline_name}' ({p_id})")
                    break
            else:
                # Stage not found in any pipeline
                attributes["deal_stage_name"] = f"Stage ID: {stage_id}"
                logger.warning(f"Stage ID {stage_id} not found in any pipeline")

        return deal_dict

    def _resolve_deal_owner(self, deal_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Resolve deal owner ID to owner details (name, email).

        Args:
            deal_record: Deal record dict with attributes

        Returns:
            Dict with name, email, id or None if not found
        """
        owner_id = deal_record.get("attributes", {}).get("deal_owner")
        if not owner_id:
            return None

        try:
            users = self.brevo_client.get_invited_users()
            owner = next((u for u in users if u["id"] == owner_id), None)

            if owner:
                # Extract name from email (daniel.lynch@brevo.com -> Daniel Lynch)
                email = owner["email"]
                name_part = email.split("@")[0]
                # Convert "daniel.lynch" to "Daniel Lynch"
                name = " ".join(word.capitalize() for word in name_part.replace(".", " ").split())

                return {
                    "id": owner_id,
                    "email": email,
                    "name": name
                }
        except Exception as e:
            logger.warning(f"Could not resolve deal owner {owner_id}: {e}")

        return None
