# Prompt Templates for Sales Action Recommendations

This directory contains prompt templates that control how AI generates action recommendations.

## Available Prompts

### `recommend.md` - Main Recommendation Prompt
Generates prioritized P0/P1/P2 action recommendations with:
- Full content for P0 actions (ready to send)
- Strategic outlines for P1/P2 actions
- Timing, prerequisites, and rationale

### `feedback.md` - Feedback Processing Prompt
Extracts learnings from user feedback to improve future recommendations.

## Customization

You can create custom prompts by:
1. Copying an existing prompt
2. Modifying the `## System Prompt` section
3. Using `--prompt-file` flag: `sales-action recommend --deal-id 123 --prompt-file my-prompt.md`

## Template Variables

Supported variables:
- `{{company_context}}` - Automatically injected company context from ~/.brevo_sales_agent/company-context.md

## Best Practices

- Be specific about output format
- Define clear priority criteria
- Include channel best practices
- Set tone and style guidelines
- Provide examples when possible
