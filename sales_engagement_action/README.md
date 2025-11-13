# Sales Engagement Action Recommender

AI-powered sales action recommendations with intelligent caching and continuous learning.

## Overview

Script 3 in the AI Sales Agent suite, this package generates prioritized, channel-specific action recommendations for sales deals with complete, ready-to-execute content.

**Key Features:**
- **P0/P1/P2 Priority Framework**: Critical actions with full content, important actions with outlines, valuable future actions
- **Intelligent 5-Hash Caching**: Tracks changes across enriched data, summaries, prompts, company context, and campaign context
- **Multi-Channel Support**: Email, phone, LinkedIn, WhatsApp with channel-specific best practices
- **Continuous Learning**: User feedback automatically updates company context to improve future recommendations
- **Seamless Integration**: Directly imports and leverages Scripts 1 (data enrichment) and 2 (deal summarization)
- **Custom Prompt Templates**: Fully customizable recommendation prompts

## Installation

```bash
# Install in development mode
cd sales_engagement_action
pip install -e .

# Verify installation
sales-action --help
```

**Prerequisites:**
- Python 3.8+
- Scripts 1 and 2 installed (`brevo-data-gatherer` and `generate-deal-summary`)
- Environment variables:
  - `ANTHROPIC_API_KEY`: Your Anthropic API key
  - `BREVO_API_KEY`: Your Brevo API key

## Quick Start

### 1. Initialize Company Context

```bash
sales-action context-init
```

This creates `~/.brevo_sales_agent/company-context.md` with a default template. Edit this file to customize:
- Company value proposition
- Product/service details
- Target audience
- Communication guidelines
- Channel-specific learnings

### 2. Generate Recommendations

```bash
# Basic recommendation
sales-action recommend 690daec017db693613964d23

# With campaign context
sales-action recommend 690daec017db693613964d23 \
  --campaign-context "Q4 product launch campaign"

# Force refresh (bypass cache)
sales-action recommend 690daec017db693613964d23 --force-refresh

# Save outputs
sales-action recommend 690daec017db693613964d23 \
  --output results.json \
  --markdown strategy.md

# Use custom prompt
sales-action recommend 690daec017db693613964d23 \
  --prompt-file custom-prompts/enterprise.md
```

### 3. Provide Feedback

```bash
# Positive feedback
sales-action feedback rec_abc123 \
  --type positive \
  --text "Email worked great, got immediate response" \
  --worked "Short subject line and clear CTA"

# Negative feedback
sales-action feedback rec_abc123 \
  --type negative \
  --text "Call was poorly timed" \
  --didnt-work "Called during their lunch hour"

# Suggested improvement
sales-action feedback rec_abc123 \
  --type neutral \
  --text "LinkedIn message could be improved" \
  --improvement "Add reference to mutual connections"
```

### 4. Manage Cache

```bash
# View cache statistics
sales-action cache-info

# Clear all cached recommendations
sales-action cache-clear --yes
```

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────┐
│                  Sales Action Recommender               │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Script 1   │ │   Script 2   │ │   Company    │
│  Enrichment  │ │  Summary     │ │   Context    │
└──────────────┘ └──────────────┘ └──────────────┘
        │               │               │
        └───────────────┴───────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │   5-Hash Cache   │
              │   Management     │
              └──────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  Claude API      │
              │  Generation      │
              └──────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  P0/P1/P2        │
              │  Recommendations │
              └──────────────────┘
```

### 5-Hash Dependency Tracking

The most sophisticated caching system across all scripts, tracking:

1. **enriched_data_hash**: CRM data from Script 1 (contact, deal, company, interactions)
2. **summary_hash**: AI-generated deal summary from Script 2
3. **prompt_hash**: Prompt template content
4. **company_context_hash**: Company context file content
5. **campaign_context_hash**: Optional campaign context parameter

**Cache invalidation occurs when:**
- ANY of the 5 hashes changes
- TTL expires (default: 60 minutes)
- User forces refresh with `--force-refresh`

### Integration with Scripts 1 & 2

Direct Python imports for seamless integration:

```python
# Script 1: Data enrichment
from brevo_data_gatherer.core.enricher import DataEnricher
enriched_data = enricher.enrich(deal_id, "deal")

# Script 2: Deal summarization
from generate_deal_summary.core.summarizer import DealSummarizer
summary = summarizer.summarize(enriched_data)
```

This leverages their existing caching automatically, creating a cascading cache system.

## Usage Guide

### Recommendation Command

```bash
sales-action recommend [OPTIONS] DEAL_ID
```

**Options:**
- `--campaign-context`, `-c`: Additional campaign context
- `--output`, `-o`: Save JSON output to file
- `--markdown`, `-m`: Save markdown strategy to file
- `--prompt-file`, `--prompt`: Use custom prompt template
- `--force-refresh`: Bypass cache and regenerate
- `--verbose`, `-v`: Verbose logging

**Output Structure:**

```
┌─────────────────────────────────────────────┐
│        Recommendation Overview              │
├─────────────────────────────────────────────┤
│ Deal            │ Enterprise SaaS Deal      │
│ Contact         │ John Smith                │
│ Engagement Level│ medium                    │
│ Deal Stage      │ qualification             │
│ P0 Actions      │ 2                         │
│ P1 Actions      │ 3                         │
│ P2 Actions      │ 2                         │
└─────────────────────────────────────────────┘

📊 Situation Analysis
- Engagement Level: medium
- Last Interaction: 2025-01-10
- Key Themes: pricing concerns, feature questions

🎯 Priority 0 Actions (Execute Today)

### Email - Address Pricing Concerns
**Timing**: Today, 2:00 PM - optimal engagement window

**Prerequisites**:
1. Review their budget from qualification call
2. Prepare ROI calculator
3. Get approval from sales manager for discount

**Full Content**:
Subject: ROI Analysis for Brevo Enterprise

[Complete email ready to send...]

⚡ Priority 1 Actions (This Week)
[Strategic outlines...]

📅 Priority 2 Actions (Next Week)
[Brief outlines...]
```

### Feedback Command

```bash
sales-action feedback [OPTIONS] RECOMMENDATION_ID
```

**Required Options:**
- `--type`, `-t`: Feedback type (positive/negative/neutral)
- `--text`: Feedback description

**Optional Options:**
- `--worked`: What worked well
- `--didnt-work`: What didn't work
- `--improvement`: Suggested improvement
- `--deal-id`: Associated deal ID
- `--priority`: Action priority (P0/P1/P2, default: P0)
- `--channel`: Action channel (email/phone/linkedin/whatsapp, default: email)
- `--verbose`, `-v`: Verbose logging

**Feedback Processing:**

1. Logs feedback to database
2. Extracts actionable learning
3. Updates appropriate section in company context
4. Increments context version
5. Future recommendations automatically use updated context

**Example Feedback Flow:**

```
Input: "Email too long, keep under 150 words"
↓
Extracted Learning: "Keep cold outreach emails under 150 words"
↓
Added to: Email Engagement Learnings section
↓
Context Version: 1.0 → 1.1
↓
All future email recommendations will follow this guideline
```

## Customization

### Custom Prompt Templates

Create custom prompts by copying and modifying `prompts/recommend.md`:

```bash
# Copy default prompt
cp sales_engagement_action/prompts/recommend.md my-prompts/enterprise.md

# Edit the prompt (modify System Prompt section)
nano my-prompts/enterprise.md

# Use custom prompt
sales-action recommend 123 --prompt-file my-prompts/enterprise.md
```

**Template Variables:**
- `{{company_context}}`: Automatically injected from `~/.brevo_sales_agent/company-context.md`

**See**: `prompts/README.md` for detailed customization guide

### Company Context Management

Edit `~/.brevo_sales_agent/company-context.md` to customize:

```markdown
# Company Context - Brevo Sales

Version: 1.0

## Company Overview
[Your company details...]

## Product/Service Details
[Your offerings...]

## Target Audience
[Your ideal customer profile...]

## Communication Guidelines
[Tone, style, best practices...]

## Email Engagement Learnings
- **2025-01-12**: Keep cold outreach under 150 words _(Context: P0 email action)_
- **2025-01-11**: Always reference mutual connections _(Context: P1 linkedin action)_

## Call Strategy Learnings
[Phone call learnings...]

## LinkedIn Outreach Learnings
[LinkedIn learnings...]

## WhatsApp Communication Learnings
[WhatsApp learnings...]
```

**Version Management:**
- Version auto-increments when feedback updates context
- Higher version numbers indicate more learnings incorporated

## Priority Framework

### P0 (Critical - Execute Today)
- **Limit**: 1-2 actions maximum
- **Content**: FULL ready-to-send content
- **Timing**: Specific time recommendations
- **Prerequisites**: Complete ordered checklist
- **Examples**:
  - Complete email with subject line and body
  - Full call script with opening, discovery, and closing
  - Ready-to-send LinkedIn/WhatsApp message

### P1 (Important - Execute This Week)
- **Limit**: 2-3 actions
- **Content**: Strategic outline only
- **Timing**: General day recommendations
- **Includes**: Key points, approach, considerations
- **Note**: Full content available on request

### P2 (Valuable - Execute Next Week)
- **Limit**: 1-3 actions
- **Content**: Brief outline only
- **Timing**: "Next week" with brief rationale
- **Note**: Full content available on request

## Caching System

### Cache Database Schema

Located at `~/.brevo_sales_agent/recommendation_cache.db`:

**recommendation_cache** table:
- `cache_key`: Composite key from all hashes
- `enriched_data_hash`: Script 1 data hash
- `summary_hash`: Script 2 summary hash
- `prompt_hash`: Prompt template hash
- `company_context_hash`: Company context hash
- `campaign_context_hash`: Campaign context hash
- `enriched_data_json`: Cached enriched data
- `summary_json`: Cached summary
- `recommendation_json`: Cached recommendations
- `generated_at`: Creation timestamp
- `expires_at`: Expiration timestamp

**feedback_log** table:
- Tracks all user feedback
- Links to recommendation_id
- Stores feedback type and content

**context_updates** table:
- Audit log of all context changes
- Links to source feedback when applicable

### Cache Statistics

```bash
sales-action cache-info
```

Shows:
- Total recommendations cached
- Fresh (valid) recommendations
- Expired (stale) recommendations
- Total feedback logged
- Total context updates
- Current TTL setting

### Cache TTL Configuration

Default: 60 minutes for recommendations

Customize in `~/.brevo_sales_agent/config.yaml`:

```yaml
cache_ttl:
  recommendations: 60  # minutes
```

## Channel Best Practices

Built-in optimization for each channel:

### Email
- **Best for**: Detailed info, proposals, content sharing
- **Optimal timing**: Tue-Thu, 10 AM - 2 PM
- **Learnings**: Continuously updated via feedback

### Phone
- **Best for**: Complex discussions, negotiations, urgency
- **Optimal timing**: Tue-Thu, 10-11 AM or 4-5 PM
- **Script structure**: Pre-call prep, opening, discovery, pitch, close

### LinkedIn
- **Best for**: New relationships, casual check-ins, content
- **Optimal timing**: Business hours, weekday mornings
- **Style**: Professional but conversational

### WhatsApp
- **Best for**: Existing relationships, quick questions, mobile-first
- **Style**: Brief, casual, emoji-friendly

## Troubleshooting

### Cache Issues

**Problem**: Recommendations not updating after context changes

**Solution**:
```bash
# Force refresh
sales-action recommend 123 --force-refresh

# Or clear entire cache
sales-action cache-clear --yes
```

### API Errors

**Problem**: "Anthropic API key not found"

**Solution**:
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

**Problem**: "Brevo API key not found"

**Solution**:
```bash
export BREVO_API_KEY="your-key-here"
```

### Missing Dependencies

**Problem**: "Cannot import DataEnricher"

**Solution**:
```bash
# Install Script 1
cd ../brevo_data_gatherer
pip install -e .
```

**Problem**: "Cannot import DealSummarizer"

**Solution**:
```bash
# Install Script 2
cd ../generate_deal_summary
pip install -e .
```

### Prompt Issues

**Problem**: Custom prompt not working

**Solution**:
- Ensure `{{company_context}}` placeholder is present
- Verify file path is correct
- Check for syntax errors in markdown

### Context Not Updating

**Problem**: Feedback not appearing in company context

**Solution**:
```bash
# Check context file exists
ls -l ~/.brevo_sales_agent/company-context.md

# Re-initialize if missing
sales-action context-init

# Check context update logs
sqlite3 ~/.brevo_sales_agent/recommendation_cache.db \
  "SELECT * FROM context_updates ORDER BY updated_at DESC LIMIT 10"
```

## Files and Structure

```
sales_engagement_action/
├── README.md                          # This file
├── setup.py                           # Package configuration
├── requirements.txt                   # Dependencies
├── config.py                          # Configuration management
├── cli.py                             # CLI interface
├── __init__.py
│
├── models/
│   ├── __init__.py
│   └── schemas.py                     # Pydantic data models
│
├── cache/
│   ├── __init__.py
│   └── manager.py                     # 5-hash cache system
│
├── core/
│   ├── __init__.py
│   ├── recommender.py                 # Main recommendation engine
│   └── feedback_processor.py         # Feedback and learning system
│
├── utils/
│   ├── __init__.py
│   ├── context_loader.py              # Company context management
│   ├── prompt_loader.py               # Prompt template loader
│   └── ai_client.py                   # Claude API client
│
└── prompts/
    ├── README.md                      # Prompt customization guide
    ├── recommend.md                   # Default recommendation prompt
    └── feedback.md                    # Feedback processing prompt
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# With coverage
pytest --cov=sales_engagement_action tests/
```

### Logging

Enable verbose logging:

```bash
sales-action recommend 123 --verbose
```

Or configure in Python:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## API Reference

### Python API

You can also use this package programmatically:

```python
from sales_engagement_action.core.recommender import ActionRecommender
from sales_engagement_action.core.feedback_processor import FeedbackProcessor
from sales_engagement_action.models.schemas import FeedbackInput
from sales_engagement_action.config import load_config

# Initialize
config = load_config()
recommender = ActionRecommender(
    anthropic_api_key=config.anthropic_api_key,
    brevo_api_key=config.brevo_api_key
)

# Generate recommendations
result = recommender.recommend(
    deal_id="690daec017db693613964d23",
    campaign_context="Q4 product launch"
)

# Access structured data
print(f"Deal: {result.deal_name}")
print(f"P0 Actions: {len(result.p0_actions)}")
for action in result.p0_actions:
    print(f"  - {action.channel}: {action.content.title}")

# Process feedback
processor = FeedbackProcessor(cache=recommender.cache)
feedback = FeedbackInput(
    recommendation_id="rec_abc123",
    feedback_type="positive",
    feedback_text="Great email!",
    action_channel="email",
    action_priority="P0"
)
result = processor.process_feedback(feedback)
```

## Related Scripts

- **Script 1**: `brevo-data-gatherer` - CRM data enrichment with caching
- **Script 2**: `generate-deal-summary` - AI-powered deal summarization

## License

Internal use only - Brevo Sales Team

## Support

For issues or questions:
1. Check this README
2. Review `prompts/README.md` for prompt customization
3. Check cache statistics with `sales-action cache-info`
4. Enable verbose logging with `--verbose`
5. Contact the AI Sales Agent development team
