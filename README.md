# Brevo Sales AI Agent

AI-powered sales engagement suite for Brevo CRM - unified package combining data enrichment, deal summarization, and next-best-action recommendations.

## Features

- 🔍 **CRM Data Enrichment** - Multi-source data gathering (Brevo API, LinkedIn, web search)
- 🤖 **AI Deal Summarization** - Claude-powered analysis and insights
- 🎯 **Smart Recommendations** - Priority-based next actions with full content
- 💾 **Intelligent Caching** - Multi-tier caching for API efficiency
- 📊 **Feedback Learning** - Continuous improvement from user feedback

## Installation

```bash
# Clone the repository
git clone https://github.com/apicolet/AI-Sales-proto.git
cd AI-Sales-proto

# Install the package
pip install -e .
```

## Configuration

### Setup Environment Variables

Create your API keys configuration at `~/.ai-sales/.env`:

```bash
# Create directory
mkdir -p ~/.ai-sales

# Copy example and edit
cp .env.example ~/.ai-sales/.env
nano ~/.ai-sales/.env
```

**Required variables:**
```bash
BREVO_API_KEY=your-brevo-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
```

**Optional variables:**
```bash
LINKEDIN_PIPEDREAM_URL=https://your-pipedream-workflow-url
SERPER_API_KEY=your-serper-api-key
BREVO_COOKIE=your-brevo-cookie  # For conversations API
```

See `.env.example` for complete documentation.

## Quick Start

### 1. Enrich CRM Data

```bash
# Enrich a contact by email
brevo-sales enrich contact@example.com

# Enrich a deal
brevo-sales enrich 61a5ce58c5d4795761045990 --type deal -o enriched.json

# Without optional integrations
brevo-sales enrich contact@example.com --no-linkedin --no-web-search
```

### 2. Generate AI Summary

```bash
# Summarize from enriched data file
brevo-sales summarize --input enriched.json -o summary.json -m report.md

# Or summarize a deal directly (enrichment + summary)
brevo-sales summarize 61a5ce58c5d4795761045990
```

### 3. Get Recommendations

```bash
# Generate next-best-action recommendations
brevo-sales recommend 690daec017db693613964d23

# With campaign context and output
brevo-sales recommend 690daec017db693613964d23 \
  --campaign-context "Q4 product launch" \
  -o recommendations.json \
  -m strategy.md
```

### 4. Provide Feedback

```bash
# Positive feedback
brevo-sales feedback rec_abc123 \
  --type positive \
  --text "Email worked great, got immediate response" \
  --worked "Short subject line and clear CTA"

# Negative feedback with improvement
brevo-sales feedback rec_abc123 \
  --type negative \
  --text "Call was poorly timed" \
  --didnt-work "Called during their lunch hour" \
  --improvement "Schedule calls between 10-11am or 2-4pm"
```

## CLI Commands

### Main Commands

| Command | Description |
|---------|-------------|
| `brevo-sales enrich` | Enrich CRM data from multiple sources |
| `brevo-sales summarize` | Generate AI-powered deal summaries |
| `brevo-sales recommend` | Get next-best-action recommendations |
| `brevo-sales feedback` | Provide feedback on recommendations |

### Utility Commands

| Command | Description |
|---------|-------------|
| `brevo-sales cache-info` | Display cache statistics |
| `brevo-sales cache-clear` | Clear cache |
| `brevo-sales context-init` | Initialize company context template |

### Get Help

```bash
brevo-sales --help
brevo-sales enrich --help
brevo-sales summarize --help
brevo-sales recommend --help
```

## Programmatic Usage

```python
from brevo_sales import DataEnricher, DealSummarizer, ActionRecommender
from brevo_sales.config import load_config

# Load configuration
load_env_from_multiple_locations()
config = load_config()

# 1. Enrich CRM data
enricher = DataEnricher(...)
enriched_data = enricher.enrich("contact@example.com")

# 2. Summarize with AI
summarizer = DealSummarizer(...)
summary = summarizer.summarize(enriched_data)

# 3. Get recommendations
recommender = ActionRecommender(...)
recommendations = recommender.recommend(deal_id="123")
```

## Project Structure

```
AI-Sales-proto/
├── setup.py                    # Package configuration
├── README.md                   # This file
├── .env.example               # Environment variables template
├── LICENSE                     # MIT License
├── CONTRIBUTING.md             # Contribution guidelines
└── src/
    └── brevo_sales/           # Main package
        ├── enrichment/        # CRM data enrichment
        ├── summarization/     # AI deal summarization
        ├── recommendations/   # Next-best-action recommendations
        ├── cache/             # Caching infrastructure
        ├── config.py          # Configuration management
        └── cli.py             # Unified CLI interface
```

## Architecture

### Three Core Modules

1. **Enrichment** - Non-AI data gathering
   - Brevo API (contacts, deals, companies, notes, tasks)
   - LinkedIn profiles (via Pipedream)
   - Web search intelligence (via Serper)
   - Smart caching with source-specific TTLs

2. **Summarization** - AI-powered analysis
   - Executive summaries
   - Stakeholder analysis
   - Opportunity and risk identification
   - Recent interaction timelines

3. **Recommendations** - Smart action suggestions
   - P0 actions (execute today) - full content
   - P1 actions (this week) - strategic outlines
   - P2 actions (next week) - brief outlines
   - Multi-channel support (email, phone, LinkedIn, WhatsApp)
   - Feedback learning loop

### Caching Strategy

| Data Source | TTL | Purpose |
|-------------|-----|---------|
| Brevo CRM | 15 min | Contact/deal/company data |
| Brevo Notes | 5 min | Frequently updated interactions |
| LinkedIn | 24 hours | Slow-changing profiles |
| Web Search | 24 hours | Company intelligence |
| Summaries | 24 hours | AI-generated insights |
| Recommendations | 1 hour | Time-sensitive actions |

## Development

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/
pytest --cov=brevo_sales tests/
```

### Code Quality

```bash
# Format code
black src/

# Lint
ruff check src/

# Type check
mypy src/
```

## Troubleshooting

### API Keys Not Found

Make sure your environment variables are set in `~/.ai-sales/.env`:

```bash
cat ~/.ai-sales/.env
```

### Import Errors

Reinstall the package in editable mode:

```bash
pip uninstall brevo-sales
pip install -e .
```

### Cache Issues

Clear the cache:

```bash
brevo-sales cache-clear --yes
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Support

- **Issues**: https://github.com/apicolet/AI-Sales-proto/issues
- **Documentation**: https://github.com/apicolet/AI-Sales-proto

---

**Built with:**
- [Anthropic Claude](https://anthropic.com) - AI summarization and recommendations
- [Brevo](https://brevo.com) - CRM platform
- [Python](https://python.org) - Core language
- [Typer](https://typer.tiangolo.com) - CLI framework
- [Pydantic](https://pydantic.dev) - Data validation
