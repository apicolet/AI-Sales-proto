# Generate Deal Summary (Script 2)

AI-powered deal summarization using enriched Brevo CRM data.

## Overview

This package takes the output from `brevo-enrich` (Script 1) and generates comprehensive, actionable deal summaries using Claude AI. It analyzes enriched CRM data to provide:

- Executive summaries
- Stakeholder analysis with engagement levels
- Opportunities, risks, and requirements
- Recent interaction timelines
- Current status and next steps context

## Installation

```bash
pip install -e .
```

## Configuration

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

Or pass it via command line with `--api-key`.

## Usage

### Basic Usage

Generate a summary from enriched data:

```bash
deal-summarize enriched_deal.json
```

### Save to File

Save JSON output:

```bash
deal-summarize enriched_deal.json -o summary.json
```

Save as markdown report:

```bash
deal-summarize enriched_deal.json -m report.md
```

### Advanced Options

Use a specific Claude model:

```bash
deal-summarize enriched_deal.json --model claude-opus-4-20250514
```

Focus on specific areas:

```bash
deal-summarize enriched_deal.json --focus "risks,opportunities"
```

Enable verbose logging:

```bash
deal-summarize enriched_deal.json -v
```

### Complete Example

```bash
# First, enrich a deal using Script 1
brevo-enrich enrich --type deal --id 123 -o enriched_deal.json

# Then generate AI summary
deal-summarize enriched_deal.json -o summary.json -m report.md
```

## Programmatic Usage

```python
from generate_deal_summary import AIClient, DealSummarizer
import json

# Load enriched data
with open('enriched_data.json') as f:
    enriched_data = json.load(f)

# Create clients
ai_client = AIClient(api_key="your-api-key")
summarizer = DealSummarizer(ai_client)

# Generate summary
summary = summarizer.summarize(enriched_data)

# Access results
print(summary.executive_summary)
print(f"Found {len(summary.opportunities)} opportunities")
print(f"Identified {len(summary.risks)} risks")

# Export to dict
summary_dict = summary.dict()
```

## Output Format

### JSON Output

```json
{
  "deal_name": "Enterprise License - Acme Corp",
  "deal_id": "123",
  "company_name": "Acme Corporation",
  "executive_summary": "High-value enterprise deal in late negotiation stage...",
  "stakeholders": [
    {
      "name": "John Smith",
      "role": "VP of Sales",
      "company": "Acme Corporation",
      "engagement_level": "high",
      "key_interests": ["Pricing flexibility", "Integration timeline"]
    }
  ],
  "opportunities": [
    {
      "category": "upsell",
      "description": "Interest in premium tier features",
      "source": "Meeting notes from 2025-01-10",
      "importance": "high"
    }
  ],
  "risks": [...],
  "requirements": [...],
  "recent_interactions": [...],
  "current_status": "Deal is progressing well with legal review underway...",
  "next_steps_context": "Follow up on contract questions by end of week...",
  "generated_at": "2025-01-15T10:30:00",
  "confidence_score": 0.85
}
```

### Markdown Report

The markdown output provides a formatted report with:

- Deal overview and metadata
- Executive summary
- Current status
- Stakeholder breakdown
- Deal context narrative
- Opportunities and risks
- Requirements list
- Recent interaction timeline
- Next steps context

## Models

### Available Claude Models

- `claude-sonnet-4-20250514` (default) - Balanced performance and cost
- `claude-opus-4-20250514` - Highest quality, deeper analysis
- `claude-haiku-4-20250514` - Fastest, most economical

### Focus Areas

You can specify focus areas to guide the AI analysis:

- `opportunities` - Emphasize growth opportunities
- `risks` - Deep dive into potential concerns
- `stakeholders` - Detailed stakeholder analysis
- `requirements` - Focus on customer needs
- `timeline` - Emphasis on temporal aspects

## Architecture

### Components

1. **AIClient** (`core/ai_client.py`)
   - Claude API integration
   - Structured output parsing
   - Error handling and retries

2. **DealSummarizer** (`core/summarizer.py`)
   - Prompt engineering
   - Data formatting
   - Summary generation
   - Fallback handling

3. **Data Models** (`models/schemas.py`)
   - DealSummary
   - Stakeholder
   - KeyInsight
   - InteractionSummary

4. **CLI** (`cli.py`)
   - Command-line interface
   - Rich formatting
   - Progress indicators
   - Output management

### Integration with Script 1

This package is designed to work seamlessly with Script 1 (brevo-enrich):

```bash
# Complete workflow
brevo-enrich enrich --type deal --id 123 -o enriched.json
deal-summarize enriched.json -o summary.json -m report.md
```

The enriched data structure from Script 1 includes:
- Primary entity (deal/contact/company)
- Related entities (contacts, companies, deals)
- Interaction history (notes, tasks)
- LinkedIn profiles (when available)
- Company information

## Error Handling

The summarizer includes comprehensive error handling:

- **API Errors**: Retries with exponential backoff
- **Parsing Errors**: Falls back to basic summary
- **Missing Data**: Gracefully handles incomplete records
- **Invalid JSON**: Extracts JSON from markdown code blocks

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Type checking
mypy generate_deal_summary/

# Linting
ruff check generate_deal_summary/

# Formatting
black generate_deal_summary/
```

## License

Proprietary - DTSL Internal Use Only
