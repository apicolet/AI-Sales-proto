"""
Integration tests for ActionParser with realistic scenarios.
"""
import pytest
import json

from brevo_sales.recommendations.parser import ActionParser, parse_recommendations
from brevo_sales.recommendations.action_models import ActionRecommendations


# Sample valid JSON response (minimal)
SAMPLE_JSON_MINIMAL = """{
  "deal_id": "deal-123",
  "deal_name": "Acme Corp Deal",
  "contact_name": "John Doe",
  "contact_email": "john@acme.com",
  "executive_summary": "High-value enterprise opportunity in evaluation phase with strong interest shown in our automated workflow features and API integration capabilities.",
  "key_insights": [
    "Decision maker attended demo personally",
    "Budget confirmed for Q4 implementation"
  ],
  "p0_actions": [
    {
      "action": {
        "type": "email",
        "from_email": "sales@company.com",
        "from_name": "Jane Smith",
        "to_email": "john@acme.com",
        "to_name": "John Doe",
        "subject": "Following up on yesterday's product demo",
        "content": "Hi John, Thank you for attending our product demo yesterday. I wanted to follow up on the questions you raised about API integration."
      },
      "priority": "P0",
      "recommended_timing": "Within 24 hours",
      "prerequisites": [],
      "rationale": "Strike while the iron is hot to maintain momentum and answer follow-up questions while demo is fresh in their mind",
      "context": "Demo completed yesterday with strong interest expressed in automated workflow features",
      "success_metrics": ["Response received within 48 hours"]
    }
  ],
  "p1_actions": [],
  "p2_actions": [],
  "overall_strategy": "Fast-track approach focusing on immediate follow-up to capitalize on strong demo engagement and technical interest shown",
  "data_version": "abc123"
}"""


class TestParserTier1:
    """Test Tier 1: Direct JSON parsing."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON directly."""
        parser = ActionParser()
        result = parser.parse(SAMPLE_JSON_MINIMAL, "deal-123", "abc123")

        assert result.success
        assert result.tier_used == 1
        assert isinstance(result.data, ActionRecommendations)
        assert result.data.deal_id == "deal-123"
        assert result.data.deal_name == "Acme Corp Deal"
        assert len(result.data.p0_actions) == 1
        assert result.data.p0_actions[0].action.type == "email"

    def test_parse_invalid_json(self):
        """Test that invalid JSON fails tier 1 and tries tier 2."""
        parser = ActionParser()
        result = parser.parse("This is not JSON", "deal-123", "abc123")

        assert not result.success
        assert result.error is not None


class TestParserTier2:
    """Test Tier 2: Markdown code block extraction."""

    def test_parse_json_in_markdown_block(self):
        """Test extracting JSON from markdown code blocks."""
        markdown_wrapped = f"""
Here are my recommendations:

```json
{SAMPLE_JSON_MINIMAL}
```

Let me know if you need anything else!
"""
        parser = ActionParser()
        result = parser.parse(markdown_wrapped, "deal-123", "abc123")

        assert result.success
        assert result.tier_used == 2
        assert isinstance(result.data, ActionRecommendations)
        assert result.data.deal_id == "deal-123"

    def test_parse_json_in_generic_code_block(self):
        """Test extracting JSON from generic code blocks."""
        markdown_wrapped = f"""
Here are my recommendations:

```
{SAMPLE_JSON_MINIMAL}
```
"""
        parser = ActionParser()
        result = parser.parse(markdown_wrapped, "deal-123", "abc123")

        assert result.success
        assert result.tier_used == 2
        assert isinstance(result.data, ActionRecommendations)

    def test_parse_multiple_code_blocks(self):
        """Test that parser tries multiple code blocks."""
        markdown_wrapped = f"""
Here's some code:

```json
{{"invalid": "json structure"}}
```

And here are the real recommendations:

```json
{SAMPLE_JSON_MINIMAL}
```
"""
        parser = ActionParser()
        result = parser.parse(markdown_wrapped, "deal-123", "abc123")

        assert result.success
        assert result.tier_used == 2
        assert result.data.deal_id == "deal-123"


class TestParserValidation:
    """Test validation and completeness checking."""

    def test_validate_completeness_warnings(self):
        """Test that validation catches data that meets schema but has quality issues."""
        # Test with valid but barely passing data (context exactly 30 chars)
        parser = ActionParser()
        result = parser.parse(SAMPLE_JSON_MINIMAL, "deal-123", "abc123")

        assert result.success

        # Validation should pass for the sample data
        warnings = parser.validate_action_completeness(result.data)
        # May have warnings but should parse successfully
        assert isinstance(warnings, list)

    def test_pydantic_validation_rejects_too_short(self):
        """Test that Pydantic validation rejects data that's too short."""
        # Create action with short rationale (will fail Pydantic validation)
        incomplete_json = SAMPLE_JSON_MINIMAL.replace(
            "Strike while the iron is hot to maintain momentum and answer follow-up questions while demo is fresh in their mind",
            "Short"  # Too short (< 50 chars)
        )

        parser = ActionParser()
        result = parser.parse(incomplete_json, "deal-123", "abc123")

        # Should fail parsing because Pydantic validation rejects it
        assert not result.success
        assert result.error is not None


class TestParserConvenienceFunction:
    """Test convenience function."""

    def test_parse_recommendations_function(self):
        """Test the convenience function works."""
        result = parse_recommendations(SAMPLE_JSON_MINIMAL, "deal-123", "abc123")

        assert result.success
        assert result.data.deal_id == "deal-123"


class TestParserErrorHandling:
    """Test error handling and fallback behavior."""

    def test_all_tiers_fail(self):
        """Test that parser fails gracefully when all tiers fail."""
        parser = ActionParser()
        result = parser.parse("Not JSON at all, no code blocks, nothing useful", "deal-123", "abc123")

        assert not result.success
        assert result.error is not None
        assert "All parsing tiers failed" in result.error

    def test_parse_result_repr(self):
        """Test ParseResult string representation."""
        result = parse_recommendations(SAMPLE_JSON_MINIMAL, "deal-123", "abc123")

        repr_str = repr(result)
        assert "success=True" in repr_str
        assert "tier=" in repr_str
