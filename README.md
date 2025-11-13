# Brevo Data Gatherer

**Script 1: Non-AI Data Enrichment Tool**

A Python package for enriching Brevo CRM entities (contacts, deals, companies) with data from multiple sources including LinkedIn and web search, featuring intelligent caching and complete data preservation.

## Features

- 🔍 **Multi-Source Enrichment**: Fetch data from Brevo API, LinkedIn (via Pipedream), and web search (Serper API)
- 💾 **Intelligent Caching**: Source-specific TTLs with SHA256-based change detection
- 🎯 **Auto-Detection**: Automatically detect entity types from identifiers
- 📦 **Complete Data**: No summarization - preserves all fetched data
- 🛠️ **Pluggable**: Optional integrations (LinkedIn, web search) can be enabled/disabled
- ⚡ **CLI Interface**: Easy-to-use command-line tool with rich output formatting

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/DTSL/brevo-data-gatherer.git
cd brevo-data-gatherer

# Install in development mode
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

### From PyPI (when published)

```bash
pip install brevo-data-gatherer
```

## Quick Start

### 1. Set Up Configuration

Create environment variables or a config file:

```bash
# Required
export BREVO_API_KEY='your-brevo-api-key'

# Optional (for LinkedIn enrichment)
export LINKEDIN_PIPEDREAM_URL='https://your-pipedream-workflow-url'

# Optional (for web search)
export SERPER_API_KEY='your-serper-api-key'
```

Or create a `config.yaml`:

```bash
brevo-enrich init-config --output config.yaml
```

### 2. Enrich an Entity

```bash
# Enrich a contact by email (auto-detect)
brevo-enrich contact@example.com

# Enrich a deal by ID
brevo-enrich 61a5ce58c5d4795761045990 --type deal

# Output to file
brevo-enrich contact@example.com --output enriched_data.json

# Without LinkedIn enrichment
brevo-enrich contact@example.com --no-linkedin

# Verbose mode
brevo-enrich contact@example.com --verbose
```

## CLI Commands

### `enrich`

Enrich a Brevo CRM entity with data from multiple sources.

```bash
brevo-enrich [ENTITY_IDENTIFIER] [OPTIONS]
```

**Arguments:**
- `ENTITY_IDENTIFIER`: Email, contact ID, deal ID, or company ID

**Options:**
- `--type, -t`: Entity type (`contact`, `deal`, `company`, or `auto`)
- `--id-type, -i`: Identifier type (`email`, `contact_id`, `deal_id`, `company_id`, or `auto`)
- `--output, -o`: Output file path (JSON format)
- `--config, -c`: Configuration file path
- `--verbose, -v`: Enable verbose logging
- `--no-linkedin`: Disable LinkedIn enrichment
- `--no-web-search`: Disable web search enrichment
- `--pretty/--compact`: Pretty-print or compact JSON output

**Examples:**

```bash
# Auto-detect contact by email
brevo-enrich service.communication@mericq.fr

# Enrich deal with output to file
brevo-enrich 61a5ce58c5d4795761045990 --type deal -o deal_data.json

# Enrich company without external integrations
brevo-enrich 61a5ce58c5d4795761045990 --type company --no-linkedin --no-web-search

# Use custom config file
brevo-enrich contact@example.com --config ./custom-config.yaml
```

### `cache-info`

Display cache statistics and information.

```bash
brevo-enrich cache-info [OPTIONS]
```

**Options:**
- `--config, -c`: Configuration file path

**Example:**

```bash
brevo-enrich cache-info
```

### `cache-clear`

Clear all cache entries.

```bash
brevo-enrich cache-clear [OPTIONS]
```

**Options:**
- `--config, -c`: Configuration file path
- `--force, -f`: Skip confirmation prompt

**Example:**

```bash
brevo-enrich cache-clear --force
```

### `cache-cleanup`

Clean up expired cache entries.

```bash
brevo-enrich cache-cleanup [OPTIONS]
```

**Options:**
- `--config, -c`: Configuration file path

**Example:**

```bash
brevo-enrich cache-cleanup
```

### `init-config`

Create a default configuration file.

```bash
brevo-enrich init-config [OPTIONS]
```

**Options:**
- `--output, -o`: Output configuration file path (default: `config.yaml`)

**Example:**

```bash
brevo-enrich init-config --output my-config.yaml
```

## Programmatic Usage

### Basic Example

```python
from brevo_data_gatherer import DataEnricher, BrevoClient, CacheManager
from brevo_data_gatherer.config import load_config

# Load configuration
config = load_config()

# Initialize cache and clients
cache_manager = CacheManager(config.cache_dir)
brevo_client = BrevoClient(
    api_key=config.brevo.api_key,
    base_url=config.brevo.base_url,
    cache_manager=cache_manager
)

# Create enricher
enricher = DataEnricher(
    brevo_client=brevo_client,
    cache_manager=cache_manager
)

# Enrich an entity
enriched_data = enricher.enrich("contact@example.com")

# Access enriched data
print(f"Entity type: {enriched_data.primary_type}")
print(f"Related contacts: {len(enriched_data.related_entities['contacts'])}")
print(f"Notes: {len(enriched_data.interaction_history['notes'])}")
print(f"API calls made: {enriched_data.metadata['api_calls_made']}")
```

### With Optional Integrations

```python
from brevo_data_gatherer import (
    DataEnricher, BrevoClient, LinkedInClient, WebSearchClient, CacheManager
)
from brevo_data_gatherer.config import load_config

# Load configuration
config = load_config()

# Initialize all clients
cache_manager = CacheManager(config.cache_dir)
brevo_client = BrevoClient(config.brevo.api_key, config.brevo.base_url, cache_manager)

# Optional: LinkedIn client
linkedin_client = None
if config.linkedin.enabled and config.linkedin.pipedream_workflow_url:
    linkedin_client = LinkedInClient(
        provider=config.linkedin.provider,
        cache_manager=cache_manager,
        pipedream_workflow_url=config.linkedin.pipedream_workflow_url
    )

# Optional: Web search client
web_client = None
if config.web_search.enabled and config.web_search.api_key:
    web_client = WebSearchClient(
        provider=config.web_search.provider,
        cache_manager=cache_manager,
        api_key=config.web_search.api_key
    )

# Create enricher with all integrations
enricher = DataEnricher(
    brevo_client=brevo_client,
    linkedin_client=linkedin_client,
    web_client=web_client,
    cache_manager=cache_manager
)

# Enrich with all sources
enriched_data = enricher.enrich("contact@example.com")
```

## Configuration

### Configuration File (config.yaml)

```yaml
# Cache directory
cache_dir: "~/.brevo_sales_agent/cache"

# Log level
log_level: "INFO"

# Brevo API configuration
brevo:
  api_key: "${BREVO_API_KEY}"
  base_url: "https://api.brevo.com/v3"

# LinkedIn integration (optional)
linkedin:
  enabled: true
  provider: "pipedream"
  pipedream_workflow_url: "${LINKEDIN_PIPEDREAM_URL}"

# Web search integration (optional)
web_search:
  enabled: true
  provider: "serper"
  api_key: "${SERPER_API_KEY}"

# Cache TTL settings
cache_ttl:
  brevo_crm: "15m"      # CRM data (contacts, deals, companies)
  brevo_notes: "5m"     # Notes
  brevo_tasks: "5m"     # Tasks
  linkedin: "24h"       # LinkedIn profiles
  web_search: "24h"     # Web search results
```

### Environment Variables

The following environment variables are supported:

- `BREVO_API_KEY` (required): Your Brevo API key
- `LINKEDIN_PIPEDREAM_URL` (optional): Pipedream workflow URL for LinkedIn enrichment
- `SERPER_API_KEY` (optional): Serper API key for web search
- `CACHE_DIR` (optional): Custom cache directory path
- `LOG_LEVEL` (optional): Logging level (DEBUG, INFO, WARNING, ERROR)

## Output Structure

The enriched data follows this structure:

```json
{
  "primary_type": "contact|deal|company",
  "primary_record": {
    // Complete primary entity data from Brevo
  },
  "related_entities": {
    "contacts": [...],
    "companies": [...],
    "deals": [...]
  },
  "interaction_history": {
    "notes": [...],
    "tasks": [...],
    "call_summaries": []
  },
  "enrichment": {
    "linkedin_profiles": {
      "contacts": [...],
      "company": {...}
    },
    "company_intelligence": {
      "key_facts": [...],
      "recent_news": [...],
      "tech_stack": [...]
    },
    "web_research": [...]
  },
  "metadata": {
    "enrichment_timestamp": "2024-01-15T10:30:00.000Z",
    "api_calls_made": 12,
    "data_quality": "high|medium|low",
    "sources_used": ["brevo_crm", "linkedin", "web_search"],
    "cache_hit_rate": 0.75,
    "duration_ms": 2500
  }
}
```

## Caching Strategy

The tool implements intelligent caching with source-specific TTLs:

| Source | TTL | Reason |
|--------|-----|--------|
| Brevo CRM | 15 minutes | Moderately changing data |
| Brevo Notes | 5 minutes | Frequently updated |
| Brevo Tasks | 5 minutes | Frequently updated |
| LinkedIn | 24 hours | Slow-changing profile data |
| Web Search | 24 hours | Slow-changing company intelligence |

**Change Detection**: Uses SHA256 hashing to detect if cached data has changed, enabling smart cache invalidation.

## Architecture

```
brevo_data_gatherer/
├── __init__.py           # Package exports
├── cli.py                # CLI interface (typer)
├── config.py             # Configuration management
├── cache/
│   ├── __init__.py
│   ├── manager.py        # Cache manager with TTL
│   └── schema.sql        # SQLite schema
├── core/
│   ├── __init__.py
│   ├── enricher.py       # Main orchestrator
│   ├── brevo_client.py   # Brevo API wrapper
│   ├── linkedin_client.py # LinkedIn integration
│   └── web_client.py     # Web search integration
└── models/
    ├── __init__.py
    └── schemas.py        # Pydantic data models
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=brevo_data_gatherer --cov-report=html
```

### Code Formatting

```bash
# Format code
black brevo_data_gatherer/

# Lint
ruff check brevo_data_gatherer/

# Type checking
mypy brevo_data_gatherer/
```

## Integration with Other Scripts

This is **Script 1** in a three-script architecture:

1. **brevo_data_gatherer** (this package) - Non-AI data collection
2. **generate_deal_summary** - AI-powered deal summarization
3. **next_best_action** - AI-powered action recommendations

Scripts communicate via structured data output (no summarization between components).

## Troubleshooting

### API Key Issues

```bash
# Check if API key is set
echo $BREVO_API_KEY

# Set API key
export BREVO_API_KEY='your-key-here'
```

### Cache Issues

```bash
# Clear all cache
brevo-enrich cache-clear --force

# Clean up expired entries
brevo-enrich cache-cleanup

# View cache statistics
brevo-enrich cache-info
```

### Verbose Logging

```bash
# Enable debug logging
brevo-enrich contact@example.com --verbose
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please see CONTRIBUTING.md for guidelines.

## Support

For issues and questions:
- GitHub Issues: https://github.com/DTSL/brevo-data-gatherer/issues
- Documentation: https://github.com/DTSL/brevo-data-gatherer/blob/HEAD/README.md
