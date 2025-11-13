"""
AI client for Claude API integration.
"""
import json
import logging
from typing import Optional, Dict, Any
import anthropic
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AIClient:
    """Client for interacting with Claude API."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-haiku-4-5-20251001",
        max_tokens: int = 4096,
        temperature: float = 0.7
    ):
        """
        Initialize AI client.

        Args:
            api_key: Anthropic API key
            model: Claude model to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Optional[type[BaseModel]] = None
    ) -> Dict[str, Any]:
        """
        Generate completion from Claude.

        Args:
            system_prompt: System instructions
            user_prompt: User message/prompt
            response_format: Optional Pydantic model for structured output

        Returns:
            Dict containing the response
        """
        try:
            logger.info(f"Calling Claude API with model: {self.model}")
            logger.debug(f"System prompt length: {len(system_prompt)} chars")
            logger.debug(f"User prompt length: {len(user_prompt)} chars")

            messages = [
                {"role": "user", "content": user_prompt}
            ]

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=messages
            )

            # Extract text content
            response_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    response_text += block.text

            logger.info(f"Received response ({len(response_text)} chars)")

            # Parse response if format specified
            if response_format:
                try:
                    # Try to extract JSON from response
                    # Look for JSON in markdown code blocks or raw JSON
                    json_text = self._extract_json(response_text)
                    parsed_data = json.loads(json_text)
                    validated_data = response_format(**parsed_data)
                    return validated_data.dict()
                except Exception as e:
                    logger.warning(f"Could not parse structured response: {e}")
                    logger.debug(f"Raw response: {response_text[:500]}...")
                    # Return raw response if parsing fails
                    return {"raw_response": response_text, "parse_error": str(e)}

            return {"response": response_text}

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Claude: {e}")
            raise

    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from text that might contain markdown code blocks.

        Args:
            text: Text potentially containing JSON

        Returns:
            Extracted JSON string
        """
        # Try to find JSON in markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                json_candidate = text[start:end].strip()
                # Check if it looks like JSON
                if json_candidate.startswith('{') or json_candidate.startswith('['):
                    return json_candidate

        # Otherwise return the full text (might be raw JSON)
        return text.strip()

    def estimate_tokens(self, text: str) -> int:
        """
        Rough estimate of token count.

        Args:
            text: Text to estimate

        Returns:
            Approximate token count
        """
        # Rough approximation: 1 token ≈ 4 characters
        return len(text) // 4
