"""
Parser for structured recommendation responses.

Implements three-tier parsing strategy:
1. Direct JSON parsing (primary)
2. Markdown code block extraction (fallback)
3. Regex pattern extraction (last resort)
"""
import json
import re
import logging
from typing import Dict, Any, Optional, Tuple, List
from pydantic import ValidationError

from brevo_sales.recommendations.action_models import (
    ActionRecommendations,
    ExecutableAction,
    EmailAction,
    PhoneAction,
    LinkedInAction,
    WhatsAppAction,
)

logger = logging.getLogger(__name__)


class ParseResult:
    """Result of parsing attempt."""

    def __init__(
        self,
        success: bool,
        data: Optional[ActionRecommendations] = None,
        tier_used: Optional[int] = None,
        error: Optional[str] = None,
        raw_response: Optional[str] = None
    ):
        self.success = success
        self.data = data
        self.tier_used = tier_used
        self.error = error
        self.raw_response = raw_response

    def __repr__(self):
        if self.success:
            return f"ParseResult(success=True, tier={self.tier_used}, actions={self.data.total_actions if self.data else 0})"
        else:
            return f"ParseResult(success=False, error={self.error[:100]}...)" if self.error and len(self.error) > 100 else f"ParseResult(success=False, error={self.error})"


class ActionParser:
    """
    Parses AI-generated recommendation responses into structured ActionRecommendations.

    Uses three-tier strategy:
    - Tier 1: Direct JSON parsing (fastest, most reliable)
    - Tier 2: Extract from markdown code blocks
    - Tier 3: Regex extraction of partial data
    """

    def __init__(self):
        """Initialize parser."""
        pass

    def parse(self, response: str, deal_id: str, data_version: str) -> ParseResult:
        """
        Parse response using three-tier strategy.

        Args:
            response: Raw text response from AI
            deal_id: Deal ID for context
            data_version: Data version hash for context

        Returns:
            ParseResult with parsed data or error
        """
        logger.info(f"Parsing response ({len(response)} chars) for deal {deal_id}")

        # Tier 1: Direct JSON parsing
        try:
            result = self._parse_tier1_direct_json(response, deal_id, data_version)
            if result.success:
                logger.info("✓ Tier 1 (direct JSON) succeeded")
                return result
        except Exception as e:
            logger.debug(f"Tier 1 failed: {e}")

        # Tier 2: Markdown code block extraction
        try:
            result = self._parse_tier2_markdown(response, deal_id, data_version)
            if result.success:
                logger.info("✓ Tier 2 (markdown extraction) succeeded")
                return result
        except Exception as e:
            logger.debug(f"Tier 2 failed: {e}")

        # Tier 3: Regex fallback
        try:
            result = self._parse_tier3_regex(response, deal_id, data_version)
            if result.success:
                logger.warning("⚠ Tier 3 (regex fallback) succeeded - data may be incomplete")
                return result
        except Exception as e:
            logger.debug(f"Tier 3 failed: {e}")

        # All tiers failed
        error_msg = "All parsing tiers failed. Response may not contain valid JSON or the format is incorrect."
        logger.error(error_msg)

        # Save raw response to file for debugging
        try:
            from pathlib import Path
            debug_file = Path("/tmp/claude_response_debug.txt")
            debug_file.write_text(response, encoding='utf-8')
            logger.error(f"Raw response saved to {debug_file} for debugging")
        except Exception as e:
            logger.warning(f"Could not save debug file: {e}")

        return ParseResult(
            success=False,
            error=error_msg,
            raw_response=response[:500]  # Include snippet for debugging
        )

    def _parse_tier1_direct_json(
        self,
        response: str,
        deal_id: str,
        data_version: str
    ) -> ParseResult:
        """
        Tier 1: Parse response as direct JSON.

        Used when AI returns pure JSON (response_format={"type": "json_object"}).
        """
        try:
            # Strip whitespace and try parsing
            data = json.loads(response.strip())

            # Validate with Pydantic
            recommendations = ActionRecommendations(**data)

            return ParseResult(
                success=True,
                data=recommendations,
                tier_used=1,
                raw_response=response
            )

        except json.JSONDecodeError as e:
            raise ValueError(f"Not valid JSON: {e}")
        except ValidationError as e:
            raise ValueError(f"JSON doesn't match schema: {e}")

    def _parse_tier2_markdown(
        self,
        response: str,
        deal_id: str,
        data_version: str
    ) -> ParseResult:
        """
        Tier 2: Extract JSON from markdown code blocks.

        Looks for ```json ... ``` or ``` ... ``` code blocks.
        """
        # Pattern 1: ```json ... ```
        pattern1 = r'```json\s*\n(.*?)\n```'
        matches1 = re.findall(pattern1, response, re.DOTALL)

        # Pattern 2: ``` ... ``` (generic code block)
        pattern2 = r'```\s*\n(.*?)\n```'
        matches2 = re.findall(pattern2, response, re.DOTALL)

        # Try all matches (json blocks first, then generic)
        all_matches = matches1 + matches2

        if not all_matches:
            raise ValueError("No markdown code blocks found")

        # Try each match
        last_error = None
        for i, json_text in enumerate(all_matches):
            try:
                data = json.loads(json_text.strip())
                recommendations = ActionRecommendations(**data)

                logger.info(f"Successfully parsed code block {i+1}/{len(all_matches)}")
                return ParseResult(
                    success=True,
                    data=recommendations,
                    tier_used=2,
                    raw_response=response
                )

            except (json.JSONDecodeError, ValidationError) as e:
                last_error = e
                logger.debug(f"Code block {i+1} failed: {e}")
                continue

        # All code blocks failed
        raise ValueError(f"All {len(all_matches)} code blocks failed to parse. Last error: {last_error}")

    def _parse_tier3_regex(
        self,
        response: str,
        deal_id: str,
        data_version: str
    ) -> ParseResult:
        """
        Tier 3: Regex fallback to extract partial data.

        Last resort - tries to extract what it can using regex patterns.
        May return incomplete data.
        """
        # Try to find anything that looks like JSON
        # Pattern: Look for { ... } structures
        pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'

        # Find the largest JSON-like structure
        matches = re.findall(pattern, response, re.DOTALL)

        if not matches:
            raise ValueError("No JSON-like structures found")

        # Sort by length (longest first)
        matches = sorted(matches, key=len, reverse=True)

        last_error = None
        for i, json_text in enumerate(matches[:5]):  # Try top 5
            try:
                data = json.loads(json_text)

                # Check if it looks like ActionRecommendations
                if 'deal_id' in data or 'p0_actions' in data:
                    # Try to validate
                    recommendations = ActionRecommendations(**data)

                    logger.warning(f"Regex fallback succeeded with match {i+1}/{min(5, len(matches))}")
                    return ParseResult(
                        success=True,
                        data=recommendations,
                        tier_used=3,
                        raw_response=response
                    )

            except (json.JSONDecodeError, ValidationError) as e:
                last_error = e
                logger.debug(f"Regex match {i+1} failed: {e}")
                continue

        raise ValueError(f"Regex extraction failed - tried {min(5, len(matches))} matches. Last error: {last_error}")

    def validate_action_completeness(self, recommendations: ActionRecommendations) -> List[str]:
        """
        Validate that all actions are complete and ready to execute.

        Returns:
            List of validation warnings (empty if all good)
        """
        warnings = []

        # Check all actions
        for priority, actions in [
            ("P0", recommendations.p0_actions),
            ("P1", recommendations.p1_actions),
            ("P2", recommendations.p2_actions)
        ]:
            for i, action in enumerate(actions):
                action_label = f"{priority} action {i+1}"

                # Check rationale length
                if len(action.rationale) < 50:
                    warnings.append(f"{action_label}: Rationale too short ({len(action.rationale)} chars)")

                # Check context length
                if len(action.context) < 30:
                    warnings.append(f"{action_label}: Context too short ({len(action.context)} chars)")

                # Check success metrics
                if not action.success_metrics:
                    warnings.append(f"{action_label}: No success metrics defined")

                # Check action-specific requirements
                if isinstance(action.action, EmailAction):
                    if len(action.action.content) < 50:
                        warnings.append(f"{action_label}: Email content too short")
                    if len(action.action.subject) < 5:
                        warnings.append(f"{action_label}: Email subject too short")

                elif isinstance(action.action, PhoneAction):
                    if len(action.action.talking_points) < 2:
                        warnings.append(f"{action_label}: Phone action needs at least 2 talking points")

        return warnings


def parse_recommendations(
    response: str,
    deal_id: str,
    data_version: str
) -> ParseResult:
    """
    Convenience function to parse recommendations.

    Args:
        response: Raw AI response text
        deal_id: Deal ID for context
        data_version: Data version hash

    Returns:
        ParseResult with parsed data or error
    """
    parser = ActionParser()
    return parser.parse(response, deal_id, data_version)
