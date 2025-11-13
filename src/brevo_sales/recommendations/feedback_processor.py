"""
Feedback processor that updates company context with learnings.
"""
import logging
import re
from pathlib import Path
from typing import Dict, Any
from brevo_sales.recommendations.models import FeedbackInput, FeedbackResult
from brevo_sales.recommendations.context_loader import CompanyContextLoader
from brevo_sales.recommendations.cache import RecommendationCache

logger = logging.getLogger(__name__)


class FeedbackProcessor:
    """Processes user feedback and updates company context with learnings."""

    def __init__(self, cache: RecommendationCache, context_file: Path):
        """
        Initialize feedback processor.

        Args:
            cache: Cache manager for logging feedback
            context_file: Path to company context file
        """
        self.cache = cache
        self.context_file = context_file

    def process_feedback(self, feedback: FeedbackInput) -> FeedbackResult:
        """
        Process feedback and update company context.

        Args:
            feedback: User feedback input

        Returns:
            FeedbackResult with update status
        """
        logger.info(f"Processing feedback for {feedback.recommendation_id}")

        try:
            # Log feedback to database
            feedback_id = self.cache.log_feedback(
                recommendation_id=feedback.recommendation_id,
                deal_id=feedback.deal_id or "unknown",
                action_priority=feedback.action_priority,
                action_channel=feedback.action_channel,
                feedback_type=feedback.feedback_type,
                feedback_text=feedback.feedback_text,
                what_worked=feedback.what_worked,
                what_didnt_work=feedback.what_didnt_work,
                suggested_improvement=feedback.suggested_improvement
            )

            # Extract learning from feedback
            learning = self._extract_learning(feedback)

            # Determine section to update
            section = self._determine_section(feedback.action_channel)

            # Update company context
            CompanyContextLoader.update_context(
                context_file=self.context_file,
                section=section,
                new_content=learning,
                append=True
            )

            # Log context update
            self.cache.log_context_update(
                update_type="learning",
                section=section,
                content=learning,
                source_feedback_id=feedback_id if feedback_id != -1 else None
            )

            # Get new version
            context_data = CompanyContextLoader.load_context(self.context_file)
            new_version = context_data["version"]

            return FeedbackResult(
                status="success",
                learning_extracted=learning,
                added_to_section=section,
                company_context_updated=True,
                new_version=new_version,
                will_apply_to=f"Future {feedback.action_channel} recommendations"
            )

        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
            return FeedbackResult(
                status="error",
                learning_extracted="",
                added_to_section="",
                company_context_updated=False,
                error_message=str(e),
                will_apply_to=""
            )

    def _extract_learning(self, feedback: FeedbackInput) -> str:
        """Extract actionable learning from feedback."""
        import datetime

        # Build learning entry
        date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Create instruction from feedback
        if feedback.feedback_type == "positive" and feedback.what_worked:
            instruction = f"{feedback.what_worked}"
        elif feedback.feedback_type == "negative" and feedback.what_didnt_work:
            instruction = f"Avoid: {feedback.what_didnt_work}"
        elif feedback.suggested_improvement:
            instruction = feedback.suggested_improvement
        else:
            instruction = feedback.feedback_text

        # Format learning entry
        context = f"{feedback.action_priority} {feedback.action_channel} action"
        learning = f"- **{date}**: {instruction} _(Context: {context})_"

        return learning

    def _determine_section(self, channel: str) -> str:
        """Determine which section to update based on channel."""
        section_map = {
            "email": "Email Engagement Learnings",
            "phone": "Call Strategy Learnings",
            "linkedin": "LinkedIn Outreach Learnings",
            "whatsapp": "WhatsApp Communication Learnings"
        }
        return section_map.get(channel, "General Learnings")
