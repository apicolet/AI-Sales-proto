# Contributing to Brevo Sales AI Agent

Thank you for contributing to the Brevo Sales AI Agent suite! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.9 or higher
- pip and virtualenv
- Git

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/DTSL/brevo-sales-ai-agent.git
cd brevo-sales-ai-agent

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all three packages in development mode
pip install -e ./brevo_data_gatherer
pip install -e ./generate_deal_summary
pip install -e ./sales_engagement_action

# Install development dependencies
pip install pytest pytest-cov black mypy ruff
```

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required
BREVO_API_KEY=your-brevo-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Optional
LINKEDIN_PIPEDREAM_URL=your-pipedream-workflow-url
SERPER_API_KEY=your-serper-api-key
```

## Development Workflow

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests**
   ```bash
   # Run tests for each package
   pytest brevo_data_gatherer/tests/
   pytest generate_deal_summary/tests/
   pytest sales_engagement_action/tests/
   ```

4. **Format and lint code**
   ```bash
   # Format with black
   black brevo_data_gatherer/ generate_deal_summary/ sales_engagement_action/

   # Lint with ruff
   ruff check brevo_data_gatherer/ generate_deal_summary/ sales_engagement_action/

   # Type check with mypy
   mypy brevo_data_gatherer/ generate_deal_summary/ sales_engagement_action/
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: descriptive message about your changes"
   ```

### Commit Message Convention

Follow conventional commits format:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions or changes
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `chore:` - Maintenance tasks

Examples:
```
feat: add support for WhatsApp channel in recommendations
fix: resolve cache invalidation issue for deal summaries
docs: update README with new CLI options
```

## Code Style Guidelines

### Python Style

- Follow PEP 8
- Use type hints for function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions focused and under 50 lines when possible

### Example

```python
from typing import Optional, Dict, Any

def enrich_contact(
    contact_id: str,
    include_linkedin: bool = True
) -> Dict[str, Any]:
    """
    Enrich a Brevo contact with additional data sources.

    Args:
        contact_id: The Brevo contact ID
        include_linkedin: Whether to fetch LinkedIn data

    Returns:
        Dictionary containing enriched contact data

    Raises:
        ValueError: If contact_id is invalid
        APIError: If Brevo API request fails
    """
    # Implementation...
    pass
```

## Project Structure

### Three-Package Architecture

1. **brevo_data_gatherer** (Script 1)
   - Non-AI data enrichment
   - Multi-source data fetching
   - Intelligent caching

2. **generate_deal_summary** (Script 2)
   - AI-powered summarization
   - Deal context analysis
   - Stakeholder identification

3. **sales_engagement_action** (Script 3)
   - Action recommendations
   - Priority-based suggestions
   - Feedback learning loop

### Adding New Features

When adding features that span multiple packages:

1. Start with the lowest-level package (brevo_data_gatherer)
2. Ensure data structures are compatible across packages
3. Update all affected READMEs
4. Add integration tests

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=brevo_data_gatherer --cov=generate_deal_summary --cov=sales_engagement_action

# Run specific test file
pytest brevo_data_gatherer/tests/test_enricher.py

# Run with verbose output
pytest -v
```

### Writing Tests

- Place tests in `tests/` directory within each package
- Name test files `test_*.py`
- Name test functions `test_*`
- Use fixtures for common setup
- Mock external API calls

Example:
```python
import pytest
from unittest.mock import Mock, patch

def test_enrich_contact_success():
    """Test successful contact enrichment."""
    # Arrange
    enricher = DataEnricher(...)

    # Act
    result = enricher.enrich("contact@example.com")

    # Assert
    assert result.primary_type == "contact"
    assert len(result.related_entities) > 0
```

## Documentation

### Updating Documentation

When making changes, update:

- Package-specific READMEs (`*/README.md`)
- Main project README
- Inline code comments
- Docstrings

### Documentation Style

- Use clear, concise language
- Include code examples
- Provide both CLI and programmatic usage examples
- Document all configuration options

## Pull Request Process

1. **Ensure all tests pass**
   ```bash
   pytest
   ```

2. **Update documentation**
   - README files
   - CHANGELOG (if exists)
   - Inline comments

3. **Create pull request**
   - Use a descriptive title
   - Reference any related issues
   - Provide context for the changes
   - Include testing steps

4. **Code review**
   - Address reviewer comments
   - Keep discussions focused
   - Be open to feedback

5. **Merge**
   - Squash commits if requested
   - Ensure CI passes
   - Delete feature branch after merge

## Reporting Issues

### Bug Reports

Include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, package versions)
- Error messages and stack traces

### Feature Requests

Include:
- Clear description of the feature
- Use case and motivation
- Proposed implementation (if applicable)
- Impact on existing functionality

## Questions?

For questions or discussions:
- Open an issue on GitHub
- Contact the maintainers
- Check existing documentation

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
