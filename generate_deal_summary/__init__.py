"""
Generate Deal Summary - Script 2

AI-powered deal summarization using enriched Brevo CRM data.

This package takes enriched data from brevo_data_gatherer (Script 1) and generates
comprehensive, actionable deal summaries using Claude AI.

Usage:
    # As a CLI tool
    $ deal-summarize enriched_data.json -o summary.json

    # Programmatically
    from generate_deal_summary import DealSummarizer, AIClient
    import json

    # Load enriched data
    with open('enriched_data.json') as f:
        enriched_data = json.load(f)

    # Create clients
    ai_client = AIClient(api_key="your-api-key")
    summarizer = DealSummarizer(ai_client)

    # Generate summary
    summary = summarizer.summarize(enriched_data)
    print(summary.executive_summary)
"""

__version__ = "1.0.0"
__author__ = "DTSL"

from generate_deal_summary.core import AIClient, DealSummarizer
from generate_deal_summary.models import DealSummary

__all__ = ["AIClient", "DealSummarizer", "DealSummary", "__version__"]
