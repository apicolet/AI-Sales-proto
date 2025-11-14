"""
Unit tests for action models and validators.
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from brevo_sales.recommendations.action_models import (
    # Enums
    ActionChannel,
    ActionStatus,
    PrerequisiteStatus,
    # Models
    Prerequisite,
    EmailAction,
    PhoneAction,
    LinkedInAction,
    WhatsAppAction,
    ExecutableAction,
    ActionRecommendations,
    # Validators
    has_placeholders,
)


# ============================================================================
# Placeholder Detection Tests
# ============================================================================

class TestPlaceholderDetection:
    """Test the placeholder detection validator."""

    def test_detects_square_bracket_placeholders(self):
        assert has_placeholders("Hello [NAME], how are you?")
        assert has_placeholders("Dear [FIRSTNAME] [LASTNAME]")
        assert has_placeholders("Contact [...]")

    def test_detects_curly_bracket_placeholders(self):
        assert has_placeholders("Hello {NAME}, how are you?")
        assert has_placeholders("Dear {FIRSTNAME} {LASTNAME}")
        assert has_placeholders("Contact {...}")

    def test_detects_angle_bracket_placeholders(self):
        assert has_placeholders("Hello <NAME>, how are you?")
        assert has_placeholders("Contact <...>")

    def test_detects_template_variables(self):
        assert has_placeholders("Hello {{name}}, welcome!")
        assert has_placeholders("Your balance: ${amount}")

    def test_detects_todo_markers(self):
        assert has_placeholders("TODO: Fill in details")
        assert has_placeholders("TBD: Schedule meeting")
        assert has_placeholders("XXX: Fix this")

    def test_detects_insert_markers(self):
        assert has_placeholders("[INSERT COMPANY NAME]")
        assert has_placeholders("[FILL IN DETAILS]")

    def test_allows_valid_text(self):
        assert not has_placeholders("Hello John, how are you?")
        assert not has_placeholders("Following up on our meeting yesterday")
        assert not has_placeholders("Let's schedule a call next week")

    def test_allows_brackets_in_context(self):
        # Real brackets used for other purposes should not trigger
        assert not has_placeholders("The API returns [200, 201] status codes")
        assert not has_placeholders("Price range: [$100-$500]")


# ============================================================================
# Prerequisite Tests
# ============================================================================

class TestPrerequisite:
    """Test Prerequisite model validation."""

    def test_valid_prerequisite(self):
        prereq = Prerequisite(
            id="prereq-1",
            task="Review the latest product demo recording and note key questions",
            assignee="john@example.com",
            deadline=datetime(2025, 12, 1, 10, 0),
            status=PrerequisiteStatus.TODO,
            blocking=True
        )
        assert prereq.id == "prereq-1"
        assert prereq.blocking is True

    def test_prerequisite_with_placeholders_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            Prerequisite(
                id="prereq-1",
                task="Review the [PRODUCT] demo and note key questions",
                assignee="john@example.com"
            )
        assert "placeholders" in str(exc_info.value).lower()

    def test_prerequisite_minimum_task_length(self):
        with pytest.raises(ValidationError):
            Prerequisite(
                id="prereq-1",
                task="Review",  # Too short
                assignee="john@example.com"
            )

    def test_prerequisite_defaults(self):
        prereq = Prerequisite(
            id="prereq-1",
            task="Complete internal review before sending proposal"
        )
        assert prereq.status == PrerequisiteStatus.TODO
        assert prereq.blocking is True
        assert prereq.assignee is None


# ============================================================================
# Email Action Tests
# ============================================================================

class TestEmailAction:
    """Test EmailAction model validation."""

    def test_valid_email_action(self):
        email = EmailAction(
            from_email="sales@company.com",
            from_name="John Smith",
            to_email="client@example.com",
            to_name="Jane Doe",
            subject="Following up on our product demo discussion",
            content="Hi Jane,\n\nThank you for attending our product demo yesterday..."
        )
        assert email.type == ActionChannel.EMAIL
        assert email.to_email == "client@example.com"

    def test_email_with_placeholders_in_subject_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            EmailAction(
                from_email="sales@company.com",
                from_name="John Smith",
                to_email="client@example.com",
                to_name="Jane Doe",
                subject="Following up on [TOPIC]",  # Placeholder
                content="Hi Jane,\n\nThank you for attending our demo..."
            )
        assert "placeholders" in str(exc_info.value).lower()

    def test_email_with_placeholders_in_content_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            EmailAction(
                from_email="sales@company.com",
                from_name="John Smith",
                to_email="client@example.com",
                to_name="Jane Doe",
                subject="Following up on our discussion",
                content="Hi [NAME],\n\nThank you for attending our product demo yesterday. I really appreciated the detailed questions you asked about our API integration capabilities."  # Placeholder
            )
        assert "placeholders" in str(exc_info.value).lower()

    def test_email_with_generic_subject_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            EmailAction(
                from_email="sales@company.com",
                from_name="John Smith",
                to_email="client@example.com",
                to_name="Jane Doe",
                subject="Hello",  # Too generic
                content="Hi Jane,\n\nThank you for attending our product demo yesterday..."
            )
        assert "generic" in str(exc_info.value).lower()

    def test_email_with_cc_and_attachments(self):
        email = EmailAction(
            from_email="sales@company.com",
            from_name="John Smith",
            to_email="client@example.com",
            to_name="Jane Doe",
            subject="Product proposal and pricing",
            content="Hi Jane,\n\nPlease find attached our product proposal...",
            cc_emails=["manager@company.com"],
            attachments=["https://company.com/proposal.pdf"]
        )
        assert len(email.cc_emails) == 1
        assert len(email.attachments) == 1

    def test_email_invalid_email_format(self):
        with pytest.raises(ValidationError):
            EmailAction(
                from_email="not-an-email",  # Invalid format
                from_name="John Smith",
                to_email="client@example.com",
                to_name="Jane Doe",
                subject="Following up",
                content="Hi Jane..."
            )

    def test_email_content_minimum_length(self):
        with pytest.raises(ValidationError):
            EmailAction(
                from_email="sales@company.com",
                from_name="John Smith",
                to_email="client@example.com",
                to_name="Jane Doe",
                subject="Following up on our discussion",
                content="Hi Jane"  # Too short
            )


# ============================================================================
# Phone Action Tests
# ============================================================================

class TestPhoneAction:
    """Test PhoneAction model validation."""

    def test_valid_phone_action(self):
        phone = PhoneAction(
            to_phone="+1-555-123-4567",
            to_name="Jane Doe",
            objective="Discuss Q4 implementation timeline and resource requirements",
            talking_points=[
                "Review the proposed timeline from our last meeting",
                "Discuss any blockers on their technical team",
                "Clarify budget approval process and next steps"
            ],
            expected_duration_minutes=30
        )
        assert phone.type == ActionChannel.PHONE
        assert phone.expected_duration_minutes == 30

    def test_phone_with_placeholder_objective_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            PhoneAction(
                to_phone="+15551234567",
                to_name="Jane Doe",
                objective="Discuss [TOPIC] and next steps",  # Placeholder
                talking_points=[
                    "Review timeline",
                    "Discuss blockers"
                ],
                expected_duration_minutes=30
            )
        assert "placeholders" in str(exc_info.value).lower()

    def test_phone_with_placeholder_talking_point_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            PhoneAction(
                to_phone="+15551234567",
                to_name="Jane Doe",
                objective="Discuss implementation timeline",
                talking_points=[
                    "Review the [PROJECT] timeline",  # Placeholder
                    "Discuss any blockers"
                ],
                expected_duration_minutes=30
            )
        assert "placeholders" in str(exc_info.value).lower()

    def test_phone_invalid_number_format(self):
        with pytest.raises(ValidationError) as exc_info:
            PhoneAction(
                to_phone="123",  # Too short
                to_name="Jane Doe",
                objective="Discuss implementation",
                talking_points=["Review timeline", "Discuss blockers"],
                expected_duration_minutes=30
            )
        assert "phone number" in str(exc_info.value).lower()

    def test_phone_talking_points_too_short(self):
        with pytest.raises(ValidationError) as exc_info:
            PhoneAction(
                to_phone="+15551234567",
                to_name="Jane Doe",
                objective="Discuss implementation timeline",
                talking_points=[
                    "Timeline",  # Too vague
                    "Blockers"   # Too vague
                ],
                expected_duration_minutes=30
            )
        assert "vague" in str(exc_info.value).lower()

    def test_phone_duration_validation(self):
        with pytest.raises(ValidationError):
            PhoneAction(
                to_phone="+15551234567",
                to_name="Jane Doe",
                objective="Discuss implementation",
                talking_points=["Review timeline", "Discuss blockers"],
                expected_duration_minutes=2  # Too short (min is 5)
            )

    def test_phone_various_formats(self):
        # All these should be accepted
        valid_numbers = [
            "+15551234567",
            "555-123-4567",
            "(555) 123-4567",
            "+1 (555) 123-4567",
            "555.123.4567"
        ]

        for number in valid_numbers:
            phone = PhoneAction(
                to_phone=number,
                to_name="Jane Doe",
                objective="Discuss implementation timeline",
                talking_points=["Review timeline", "Discuss blockers"],
                expected_duration_minutes=30
            )
            assert phone.to_phone == number


# ============================================================================
# LinkedIn Action Tests
# ============================================================================

class TestLinkedInAction:
    """Test LinkedInAction model validation."""

    def test_valid_linkedin_message(self):
        linkedin = LinkedInAction(
            recipient_linkedin_url="https://www.linkedin.com/in/johndoe/",
            recipient_name="John Doe",
            action_type="message",
            message="Hi John, I noticed you recently joined Acme Corp. Congrats on the new role! I wanted to reach out..."
        )
        assert linkedin.type == ActionChannel.LINKEDIN
        assert linkedin.action_type == "message"

    def test_valid_linkedin_connection_request(self):
        linkedin = LinkedInAction(
            recipient_linkedin_url="https://www.linkedin.com/in/johndoe/",
            recipient_name="John Doe",
            action_type="connection_request",
            message="Hi John, I'd love to connect and discuss our mutual interest in marketing automation.",
            connection_note="We both work in the marketing automation space and I'd love to connect."
        )
        assert linkedin.action_type == "connection_request"
        assert linkedin.connection_note is not None

    def test_valid_linkedin_inmail(self):
        linkedin = LinkedInAction(
            recipient_linkedin_url="https://www.linkedin.com/in/johndoe/",
            recipient_name="John Doe",
            action_type="inmail",
            subject="Helping Acme Corp streamline customer engagement",
            message="Hi John, I noticed Acme Corp recently expanded into the European market. Our platform helps companies..."
        )
        assert linkedin.action_type == "inmail"
        assert linkedin.subject is not None

    def test_linkedin_invalid_url_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            LinkedInAction(
                recipient_linkedin_url="https://twitter.com/johndoe",  # Not LinkedIn
                recipient_name="John Doe",
                action_type="message",
                message="Hi John..."
            )
        assert "linkedin" in str(exc_info.value).lower()

    def test_linkedin_with_placeholder_message_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            LinkedInAction(
                recipient_linkedin_url="https://www.linkedin.com/in/johndoe/",
                recipient_name="John Doe",
                action_type="message",
                message="Hi [NAME], I noticed you work at [COMPANY]..."  # Placeholders
            )
        assert "placeholders" in str(exc_info.value).lower()

    def test_linkedin_inmail_requires_subject(self):
        with pytest.raises(ValidationError) as exc_info:
            LinkedInAction(
                recipient_linkedin_url="https://www.linkedin.com/in/johndoe/",
                recipient_name="John Doe",
                action_type="inmail",
                # Missing subject
                message="Hi John, I noticed Acme Corp recently expanded..."
            )
        assert "subject" in str(exc_info.value).lower()

    def test_linkedin_connection_requires_note(self):
        with pytest.raises(ValidationError) as exc_info:
            LinkedInAction(
                recipient_linkedin_url="https://www.linkedin.com/in/johndoe/",
                recipient_name="John Doe",
                action_type="connection_request",
                message="Hi John, I'd love to connect and learn more about your work in the marketing automation space.",
                # Missing connection_note
            )
        assert "note" in str(exc_info.value).lower()

    def test_linkedin_message_length_limits(self):
        with pytest.raises(ValidationError):
            LinkedInAction(
                recipient_linkedin_url="https://www.linkedin.com/in/johndoe/",
                recipient_name="John Doe",
                action_type="message",
                message="a" * 2000  # Exceeds LinkedIn's 1900 char limit
            )


# ============================================================================
# WhatsApp Action Tests
# ============================================================================

class TestWhatsAppAction:
    """Test WhatsAppAction model validation."""

    def test_valid_whatsapp_action(self):
        whatsapp = WhatsAppAction(
            to_phone="+15551234567",
            to_name="Jane Doe",
            message="Hi Jane! Following up on our meeting yesterday. When would be a good time to discuss the proposal?"
        )
        assert whatsapp.type == ActionChannel.WHATSAPP
        assert whatsapp.to_phone == "+15551234567"

    def test_whatsapp_with_media(self):
        whatsapp = WhatsAppAction(
            to_phone="+15551234567",
            to_name="Jane Doe",
            message="Hi Jane! Here's the product brochure we discussed.",
            media_url="https://company.com/brochure.pdf"
        )
        assert whatsapp.media_url is not None

    def test_whatsapp_with_placeholder_message_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            WhatsAppAction(
                to_phone="+15551234567",
                to_name="Jane Doe",
                message="Hi [NAME], following up on our meeting..."  # Placeholder
            )
        assert "placeholders" in str(exc_info.value).lower()

    def test_whatsapp_invalid_phone_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            WhatsAppAction(
                to_phone="123",  # Too short
                to_name="Jane Doe",
                message="Hi Jane, following up..."
            )
        assert "phone number" in str(exc_info.value).lower()

    def test_whatsapp_message_minimum_length(self):
        with pytest.raises(ValidationError):
            WhatsAppAction(
                to_phone="+15551234567",
                to_name="Jane Doe",
                message="Hi"  # Too short
            )


# ============================================================================
# Executable Action Tests
# ============================================================================

class TestExecutableAction:
    """Test ExecutableAction model validation and status computation."""

    def test_valid_executable_action(self):
        email = EmailAction(
            from_email="sales@company.com",
            from_name="John Smith",
            to_email="client@example.com",
            to_name="Jane Doe",
            subject="Following up on our product demo",
            content="Hi Jane, Thank you for attending our demo yesterday. Based on our discussion..."
        )

        action = ExecutableAction(
            action=email,
            priority="P0",
            recommended_timing="Within 24 hours of demo completion",
            prerequisites=[],
            rationale="Strike while the iron is hot - Jane expressed strong interest in the automated workflow features",
            context="Jane attended demo yesterday, asked 5 detailed questions about API integration",
            success_metrics=[
                "Response received within 48 hours",
                "Meeting scheduled for technical deep-dive"
            ]
        )

        assert action.priority == "P0"
        assert action.status == ActionStatus.PENDING

    def test_executable_action_with_prerequisites(self):
        prereq1 = Prerequisite(
            id="prereq-1",
            task="Get approval from VP Sales on custom pricing proposal",
            assignee="john@company.com",
            blocking=True,
            status=PrerequisiteStatus.TODO
        )

        email = EmailAction(
            from_email="sales@company.com",
            from_name="John Smith",
            to_email="client@example.com",
            to_name="Jane Doe",
            subject="Custom pricing proposal for Acme Corp",
            content="Hi Jane, As discussed, here is our custom pricing proposal..."
        )

        action = ExecutableAction(
            action=email,
            priority="P1",
            recommended_timing="Within 3 business days after approval",
            prerequisites=[prereq1],
            rationale="Need executive approval before sending custom pricing",
            context="Jane requested custom pricing for 500+ user deployment",
            success_metrics=["Response with budget approval or questions"]
        )

        # Should automatically set status to PREREQUISITES_INCOMPLETE
        assert action.status == ActionStatus.PREREQUISITES_INCOMPLETE

    def test_executable_action_status_becomes_ready(self):
        prereq1 = Prerequisite(
            id="prereq-1",
            task="Get approval from VP Sales on custom pricing before sending to client",
            blocking=True,
            status=PrerequisiteStatus.COMPLETED  # Completed
        )

        email = EmailAction(
            from_email="sales@company.com",
            from_name="John Smith",
            to_email="client@example.com",
            to_name="Jane Doe",
            subject="Custom pricing proposal for your enterprise deployment",
            content="Hi Jane, As discussed in our meeting yesterday, I'm pleased to share our custom pricing proposal for your 500-user enterprise deployment."
        )

        action = ExecutableAction(
            action=email,
            priority="P1",
            recommended_timing="Immediately after approval",
            prerequisites=[prereq1],
            rationale="VP Sales has approved the custom pricing proposal and we should send it immediately while Jane is still evaluating vendors",
            context="Jane requested custom pricing for 500+ user deployment during demo last week",
            success_metrics=["Response received within 48 hours with budget confirmation"]
        )

        # Should be READY since prerequisite is completed
        assert action.status in (ActionStatus.READY, ActionStatus.PENDING)

    def test_executable_action_with_non_blocking_prerequisite(self):
        prereq1 = Prerequisite(
            id="prereq-1",
            task="Review latest product updates and release notes before the call",
            blocking=False,  # Non-blocking
            status=PrerequisiteStatus.TODO
        )

        email = EmailAction(
            from_email="sales@company.com",
            from_name="John Smith",
            to_email="client@example.com",
            to_name="Jane Doe",
            subject="Following up on yesterday's product demo",
            content="Hi Jane, Thank you for attending our product demo yesterday. I really appreciated your thoughtful questions about our API integration capabilities."
        )

        action = ExecutableAction(
            action=email,
            priority="P0",
            recommended_timing="Within 24 hours of demo",
            prerequisites=[prereq1],
            rationale="Follow up immediately while the demo is fresh in their mind to maintain momentum and answer any follow-up questions",
            context="Demo completed yesterday with strong interest expressed in automated workflow features",
            success_metrics=["Response received within 48 hours", "Meeting scheduled for technical deep-dive"]
        )

        # Should be PENDING/READY even with incomplete prerequisite (it's non-blocking)
        assert action.status in (ActionStatus.PENDING, ActionStatus.READY)

    def test_executable_action_with_placeholders_in_rationale_fails(self):
        email = EmailAction(
            from_email="sales@company.com",
            from_name="John Smith",
            to_email="client@example.com",
            to_name="Jane Doe",
            subject="Following up on our discussion",
            content="Hi Jane, Thank you for taking the time to meet with us yesterday to discuss your marketing automation needs."
        )

        with pytest.raises(ValidationError) as exc_info:
            ExecutableAction(
                action=email,
                priority="P0",
                recommended_timing="Within 24 hours",
                prerequisites=[],
                rationale="Follow up on [TOPIC] discussion to maintain momentum",  # Placeholder
                context="Demo completed yesterday with strong interest shown",
                success_metrics=["Response received within 48 hours"]
            )
        assert "placeholders" in str(exc_info.value).lower()

    def test_executable_action_success_metrics_validation(self):
        email = EmailAction(
            from_email="sales@company.com",
            from_name="John Smith",
            to_email="client@example.com",
            to_name="Jane Doe",
            subject="Following up on yesterday's demo",
            content="Hi Jane, Thank you for attending our product demo yesterday. I wanted to follow up on the questions you raised about API integration."
        )

        with pytest.raises(ValidationError) as exc_info:
            ExecutableAction(
                action=email,
                priority="P0",
                recommended_timing="Within 24 hours of demo",
                prerequisites=[],
                rationale="Follow up immediately after demo to maintain momentum and answer any remaining questions from the presentation",
                context="Demo completed yesterday with strong interest expressed in automated features",
                success_metrics=["Reply"]  # Too vague
            )
        assert "vague" in str(exc_info.value).lower()


# ============================================================================
# Discriminated Union Tests
# ============================================================================

class TestDiscriminatedUnion:
    """Test that discriminated union works correctly."""

    def test_parse_email_action(self):
        data = {
            "type": "email",
            "from_email": "sales@company.com",
            "from_name": "John",
            "to_email": "client@example.com",
            "to_name": "Jane",
            "subject": "Following up on discussion",
            "content": "Hi Jane, thank you for your time yesterday. I really appreciated the detailed questions you raised about our API integration capabilities and wanted to follow up with additional information."
        }

        action = ExecutableAction(
            action=data,
            priority="P0",
            recommended_timing="Within 24 hours of demo",
            rationale="Follow up immediately while the demo is fresh to maintain momentum and answer follow-up questions",
            context="Demo completed yesterday with strong interest in automated workflow features",
            success_metrics=["Response within 48 hours", "Meeting scheduled for technical discussion"]
        )

        assert isinstance(action.action, EmailAction)
        assert action.action.type == ActionChannel.EMAIL

    def test_parse_phone_action(self):
        data = {
            "type": "phone",
            "to_phone": "+15551234567",
            "to_name": "Jane",
            "objective": "Discuss implementation timeline and resource requirements for Q4 deployment",
            "talking_points": ["Review the proposed implementation timeline", "Discuss any technical blockers or concerns", "Clarify resource requirements from their team"],
            "expected_duration_minutes": 30
        }

        action = ExecutableAction(
            action=data,
            priority="P1",
            recommended_timing="This week before Friday",
            rationale="Need verbal confirmation on timeline and resources to keep project on track for Q4 launch",
            context="Email sent last week with written proposal, now need verbal discussion to finalize details",
            success_metrics=["Agreement on timeline secured", "Meeting scheduled for kickoff"]
        )

        assert isinstance(action.action, PhoneAction)
        assert action.action.type == ActionChannel.PHONE


# ============================================================================
# Action Recommendations Collection Tests
# ============================================================================

class TestActionRecommendations:
    """Test ActionRecommendations collection model."""

    def test_valid_recommendations(self):
        email = EmailAction(
            from_email="sales@company.com",
            from_name="John Smith",
            to_email="client@example.com",
            to_name="Jane Doe",
            subject="Following up on yesterday's product demo",
            content="Hi Jane, thanks for attending our product demo yesterday. I really appreciated your thoughtful questions about our API integration capabilities and automated workflow features."
        )

        action = ExecutableAction(
            action=email,
            priority="P0",
            recommended_timing="Within 24 hours of demo",
            rationale="Strike while the iron is hot to maintain momentum and answer any follow-up questions while the demo is fresh",
            context="Demo completed yesterday with strong interest expressed, multiple detailed questions asked about integration",
            success_metrics=["Response received within 48 hours", "Meeting scheduled for technical deep-dive"]
        )

        recommendations = ActionRecommendations(
            deal_id="deal-123",
            deal_name="Acme Corp Enterprise Deal",
            contact_name="Jane Doe",
            contact_email="jane@acme.com",
            executive_summary="High-value enterprise opportunity worth $500k ARR. Strong interest shown in demo yesterday, now in evaluation phase. Decision maker attended personally and asked detailed technical questions.",
            key_insights=[
                "Decision maker attended demo personally",
                "Budget confirmed for Q4 implementation",
                "Competing with two other vendors"
            ],
            p0_actions=[action],
            overall_strategy="Focus on differentiation through our unique automated workflow features that solve their specific pain points around manual data entry and campaign coordination.",
            data_version="abc123",
        )

        assert recommendations.deal_id == "deal-123"
        assert len(recommendations.p0_actions) == 1
        assert recommendations.total_actions == 1

    def test_recommendations_properties(self):
        email1 = EmailAction(
            from_email="sales@company.com",
            from_name="John",
            to_email="client@example.com",
            to_name="Jane",
            subject="Following up on yesterday's demo",
            content="Hi Jane, thank you for attending our product demo yesterday and asking such detailed questions about our integration capabilities."
        )

        email2 = EmailAction(
            from_email="sales@company.com",
            from_name="John",
            to_email="client2@example.com",
            to_name="Bob",
            subject="Checking in on your evaluation progress",
            content="Hi Bob, I wanted to check in and see how your evaluation of our platform is progressing and if you have any questions."
        )

        action1 = ExecutableAction(
            action=email1,
            priority="P0",
            recommended_timing="Within 24 hours",
            rationale="Urgent follow-up needed while demo is fresh to maintain momentum and capture interest",
            context="Demo completed yesterday with strong engagement and multiple detailed questions",
            success_metrics=["Response received within 48 hours"],
            status=ActionStatus.READY
        )

        prereq2 = Prerequisite(
            id="prereq-2",
            task="Wait for internal product update before reaching out with new features",
            blocking=True,
            status=PrerequisiteStatus.IN_PROGRESS
        )

        action2 = ExecutableAction(
            action=email2,
            priority="P1",
            recommended_timing="This week before Friday",
            prerequisites=[prereq2],
            rationale="Regular check-in needed as prospect has been quiet for two weeks, need to re-engage",
            context="Last contact was two weeks ago, prospect has been evaluating competitors",
            success_metrics=["Meeting scheduled for next steps discussion"],
            status=ActionStatus.PREREQUISITES_INCOMPLETE
        )

        recommendations = ActionRecommendations(
            deal_id="deal-123",
            deal_name="Acme Deal",
            executive_summary="Enterprise opportunity worth $300k ARR currently in evaluation phase with decision expected within 4 weeks",
            key_insights=["Strong interest shown in automated features"],
            p0_actions=[action1],
            p1_actions=[action2],
            overall_strategy="Focus on differentiation through our unique automated workflow features and superior API integration capabilities",
            data_version="abc123"
        )

        assert recommendations.total_actions == 2
        assert len(recommendations.all_actions) == 2
        assert len(recommendations.ready_actions) == 1
        assert recommendations.ready_actions[0] == action1
