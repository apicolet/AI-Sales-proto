"""
Sales Engagement Action Recommender - Script 3

Generates prioritized next-best-action recommendations for sales engagement
based on enriched CRM data, deal summaries, and company context.

Usage:
    # As a CLI tool
    $ sales-action recommend 690daec017db693613964d23 -o results.json

    # Programmatically
    from sales_engagement_action import ActionRecommender, FeedbackProcessor
    from sales_engagement_action.config import load_config

    config = load_config()
    recommender = ActionRecommender(
        anthropic_api_key=config.anthropic_api_key,
        brevo_api_key=config.brevo_api_key
    )

    result = recommender.recommend(deal_id="123", campaign_context="Q4 launch")
"""

__version__ = "0.1.0"
__author__ = "DTSL"

# Core exports
from sales_engagement_action.core.recommender import ActionRecommender
from sales_engagement_action.core.feedback_processor import FeedbackProcessor

# Model exports
from sales_engagement_action.models.schemas import (
    RecommendationResult,
    ActionRecommendation,
    FeedbackInput
)

__all__ = [
    "ActionRecommender",
    "FeedbackProcessor",
    "RecommendationResult",
    "ActionRecommendation",
    "FeedbackInput",
    "__version__",
]
