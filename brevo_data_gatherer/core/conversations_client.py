"""
Brevo Conversations API client (frontend/cookie-based).

Fetches email conversation data from Brevo's deal timeline API
using cookie-based authentication.
"""
import requests
import logging
from typing import List, Dict, Any, Optional
import urllib3

from brevo_data_gatherer.models.schemas import ConversationMessage, ConversationEmail
from brevo_data_gatherer.cache.manager import CacheManager

# Disable SSL warnings for internal API calls
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class ConversationsClient:
    """
    Brevo Conversations API client with cookie authentication.

    Uses cookie-based authentication to access frontend APIs that
    don't have public API endpoints.
    """

    def __init__(
        self,
        cookie_string: str,
        backend_url: str,
        cache_manager: Optional[CacheManager] = None
    ):
        """
        Initialize conversations client.

        Args:
            cookie_string: Full cookie string from browser session
            backend_url: Brevo backend API base URL
            cache_manager: Optional cache manager for caching responses
        """
        self.backend_url = backend_url.rstrip('/')
        self.cache_manager = cache_manager

        # Parse cookie string into dict
        self.cookies = {}
        for item in cookie_string.split('; '):
            if '=' in item:
                key, value = item.split('=', 1)
                self.cookies[key] = value

        # Setup session with EXACT headers only (no automatic additions)
        self.session = requests.Session()
        self.session.cookies.update(self.cookies)

        # Clear all default headers to prevent automatic additions
        self.session.headers.clear()

        # Set EXACT headers as specified - do not add or modify
        self.session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Origin": "https://app.brevo.com",
            "Referer": "https://app.brevo.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"'
        })

        logger.info(f"ConversationsClient initialized with {len(self.cookies)} cookies")

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
            entity_type: Entity type
            entity_id: Entity ID
            fetch_func: Function to call if cache miss

        Returns:
            Data from cache or API
        """
        # Try cache first
        if self.cache_manager:
            cached = self.cache_manager.get(source, entity_type, entity_id)
            if cached:
                logger.info(f"Using cached conversations for {entity_type} {entity_id}")
                return cached["data"]

        # Cache miss - fetch from API
        logger.info(f"Fetching {entity_type} {entity_id} from {source}")
        data = fetch_func()

        # Store in cache
        if self.cache_manager:
            self.cache_manager.set(source, entity_type, entity_id, data)

        return data

    def get_deal_timeline(
        self,
        deal_id: str,
        limit: int = 50,
        planned: int = 0
    ) -> Dict[str, Any]:
        """
        Fetch the timeline for a given deal ID.

        Args:
            deal_id: The deal ID to fetch timeline for
            limit: Maximum number of timeline items to fetch
            planned: 0 for past activities, 1 for planned activities

        Returns:
            Timeline data dictionary

        Raises:
            requests.HTTPError: If the request fails
        """
        cache_key = f"{deal_id}:planned_{planned}"

        def fetch():
            url = f"{self.backend_url}/crm/backend/deals/timeline"
            params = {
                "dealId": deal_id,
                "planned": str(planned),
                "limit": limit,
                "withCount": "false"
            }

            # Debug logging - show full request details
            logger.debug(f"=== Conversations API Request Debug ===")
            logger.debug(f"URL: {url}")
            logger.debug(f"Params: {params}")
            logger.debug(f"Headers: {dict(self.session.headers)}")
            logger.debug(f"Cookies ({len(self.session.cookies)} total):")
            for cookie in self.session.cookies:
                logger.debug(f"  {cookie.name}={cookie.value[:50]}..." if len(cookie.value) > 50 else f"  {cookie.name}={cookie.value}")

            # Generate complete CURL command for debugging
            import urllib.parse
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            curl_cmd = f"curl -X GET '{full_url}' \\\n"

            # Add headers
            for header_name, header_value in self.session.headers.items():
                curl_cmd += f"  -H '{header_name}: {header_value}' \\\n"

            # Add cookies as a single Cookie header
            cookie_string = "; ".join([f"{cookie.name}={cookie.value}" for cookie in self.session.cookies])
            curl_cmd += f"  -H 'Cookie: {cookie_string}' \\\n"
            curl_cmd += "  --compressed \\\n"
            curl_cmd += "  --insecure"

            logger.debug(f"\n=== COMPLETE CURL COMMAND ===\n{curl_cmd}\n==============================")
            logger.debug(f"=======================================")

            try:
                response = self.session.get(
                    url,
                    params=params,
                    verify=False,
                    timeout=30
                )

                # Log response status
                logger.debug(f"Response status: {response.status_code}")

                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code in (401, 403):
                    logger.error(
                        f"Authentication failed (cookie expired?): {e.response.status_code}. "
                        "Please update BREVO_COOKIE environment variable."
                    )
                    # Log response body for debugging
                    logger.debug(f"Response body: {e.response.text[:500]}")
                raise
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch deal timeline: {e}")
                raise

        return self._get_cached_or_fetch(
            "brevo_conversations",
            "deal_timeline",
            cache_key,
            fetch
        )

    def extract_conversations(
        self,
        timeline_data: Dict[str, Any]
    ) -> List[ConversationEmail]:
        """
        Extract email conversations from timeline data.

        Args:
            timeline_data: Raw timeline data from get_deal_timeline()

        Returns:
            List of ConversationEmail objects grouped by conversation
        """
        conversations_map: Dict[str, ConversationEmail] = {}

        for item in timeline_data.get('items', []):
            if item.get('activityType') != 'conversations_email':
                continue

            entity = item.get('entity', {})
            props = entity.get('event_properties', {})
            visitor = props.get('visitor', {})

            conversation_id = props.get('conversationId')
            if not conversation_id:
                logger.warning("Skipping email item without conversation ID")
                continue

            # Create conversation if not exists
            if conversation_id not in conversations_map:
                conversations_map[conversation_id] = ConversationEmail(
                    conversation_id=conversation_id,
                    thread_link=visitor.get('threadLink'),
                    contact_id=entity.get('contact_id'),
                    visitor_name=visitor.get('displayedName'),
                    messages=[],
                    first_message_date=item.get('date'),
                    last_message_date=item.get('date'),
                    message_count=0
                )

            # Extract messages from this timeline item
            for msg in props.get('messages', []):
                message = ConversationMessage(
                    date=item.get('date'),
                    contact_id=entity.get('contact_id'),
                    visitor_name=visitor.get('displayedName'),
                    conversation_id=conversation_id,
                    thread_link=visitor.get('threadLink'),
                    from_email=msg.get('from', {}).get('email') if msg.get('from') else None,
                    from_name=msg.get('from', {}).get('name') if msg.get('from') else None,
                    to_email=msg.get('to', [{}])[0].get('email') if msg.get('to') else None,
                    to_name=msg.get('to', [{}])[0].get('name') if msg.get('to') else None,
                    subject=msg.get('subject'),
                    html_body=msg.get('html'),
                    created_at=msg.get('createdAt'),
                    message_type=msg.get('type'),
                    agent_name=msg.get('agentName')
                )

                conversations_map[conversation_id].messages.append(message)
                conversations_map[conversation_id].message_count += 1

                # Update date range
                msg_date = item.get('date')
                if msg_date:
                    conv = conversations_map[conversation_id]
                    if not conv.first_message_date or msg_date < conv.first_message_date:
                        conv.first_message_date = msg_date
                    if not conv.last_message_date or msg_date > conv.last_message_date:
                        conv.last_message_date = msg_date

        result = list(conversations_map.values())
        logger.info(f"Extracted {len(result)} conversations with {sum(c.message_count for c in result)} total messages")

        return result

    def get_deal_conversations(
        self,
        deal_id: str,
        limit: int = 50
    ) -> List[ConversationEmail]:
        """
        Get all email conversations for a deal.

        This is a convenience method that combines get_deal_timeline
        and extract_conversations.

        Args:
            deal_id: The deal ID to fetch conversations for
            limit: Maximum number of timeline items to fetch

        Returns:
            List of ConversationEmail objects
        """
        try:
            timeline = self.get_deal_timeline(deal_id, limit=limit)
            conversations = self.extract_conversations(timeline)
            return conversations
        except Exception as e:
            logger.error(f"Failed to get conversations for deal {deal_id}: {e}")
            return []
