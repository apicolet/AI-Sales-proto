# Brevo Data Gatherer

**Script 1: Non-AI Data Enrichment Tool**

Multi-source data enrichment for Brevo CRM entities (contacts, deals, companies) with intelligent caching.

## Features

- 🔍 Multi-source enrichment (Brevo API, LinkedIn, web search)
- 💾 Intelligent caching with source-specific TTLs
- 🎯 Auto-detection of entity types
- 📦 Complete data preservation (no summarization)
- ⚡ CLI interface with rich formatting

## Installation

```bash
# Install in development mode
cd brevo_data_gatherer
pip install -e .
```

## Quick Start

```bash
# Set environment variables
export BREVO_API_KEY='your-brevo-api-key'
export LINKEDIN_PIPEDREAM_URL='your-pipedream-url'  # Optional
export SERPER_API_KEY='your-serper-key'             # Optional

# Enrich a contact
brevo-enrich contact@example.com

# Enrich a deal
brevo-enrich 61a5ce58c5d4795761045990 --type deal -o deal_data.json

# View cache statistics
brevo-enrich cache-info
```

## CLI Commands

### `enrich`
```bash
brevo-enrich [ENTITY_IDENTIFIER] [OPTIONS]
```

**Options:**
- `--type, -t`: Entity type (contact, deal, company, auto)
- `--output, -o`: Output file path
- `--verbose, -v`: Verbose logging
- `--no-linkedin`: Disable LinkedIn enrichment
- `--no-web-search`: Disable web search

### Cache Management
```bash
brevo-enrich cache-info      # View cache statistics
brevo-enrich cache-clear     # Clear cache
brevo-enrich cache-cleanup   # Clean expired entries
```

## Programmatic Usage

```python
from brevo_data_gatherer import DataEnricher, BrevoClient, CacheManager
from brevo_data_gatherer.config import load_config

# Load configuration
config = load_config()

# Initialize
cache_manager = CacheManager(config.cache_dir)
brevo_client = BrevoClient(
    api_key=config.brevo.api_key,
    cache_manager=cache_manager
)

# Create enricher
enricher = DataEnricher(
    brevo_client=brevo_client,
    cache_manager=cache_manager
)

# Enrich entity
data = enricher.enrich("contact@example.com")
print(f"Found {len(data.related_entities['contacts'])} related contacts")
```

## Output Structure

```json
{
  "primary_type": "contact|deal|company",
  "primary_record": { ... },
  "related_entities": {
    "contacts": [...],
    "companies": [...],
    "deals": [...]
  },
  "interaction_history": {
    "notes": [...],
    "tasks": [...]
  },
  "enrichment": {
    "linkedin_profiles": { ... },
    "company_intelligence": { ... }
  },
  "metadata": {
    "enrichment_timestamp": "...",
    "api_calls_made": 12,
    "sources_used": ["brevo_crm", "linkedin"],
    "cache_hit_rate": 0.75
  }
}
```

## Caching Strategy

| Source | TTL | Reason |
|--------|-----|--------|
| Brevo CRM | 15 minutes | Moderately changing |
| Brevo Notes | 5 minutes | Frequently updated |
| LinkedIn | 24 hours | Slow-changing profiles |
| Web Search | 24 hours | Slow-changing intelligence |

## Integration

This is **Script 1** in a three-script architecture:

1. **brevo_data_gatherer** (this package) - Data enrichment
2. **generate_deal_summary** - AI summarization
3. **sales_engagement_action** - Action recommendations

Pass enriched data to Script 2:
```bash
brevo-enrich contact@example.com -o enriched.json
deal-summarize enriched.json -o summary.json
```

## Configuration

Create `~/.brevo_sales_agent/config.yaml`:

```yaml
cache_dir: "~/.brevo_sales_agent/cache"
log_level: "INFO"

brevo:
  api_key: "${BREVO_API_KEY}"
  base_url: "https://api.brevo.com/v3"

linkedin:
  enabled: true
  pipedream_workflow_url: "${LINKEDIN_PIPEDREAM_URL}"

web_search:
  enabled: true
  provider: "serper"
  api_key: "${SERPER_API_KEY}"

cache_ttl:
  brevo_crm: "15m"
  brevo_notes: "5m"
  linkedin: "24h"
  web_search: "24h"
```

## License

MIT License - See LICENSE file in repository root
