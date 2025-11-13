# Custom Prompt Templates

This directory contains prompt templates for AI-powered deal summarization. Prompts allow you to customize the analysis style, output format, and focus areas to match your specific use case.

## Quick Start

### Using the Default Prompt

```bash
# Uses the built-in default prompt automatically
deal-summarize --deal-id 123
```

### Using a Custom Prompt

```bash
# Use a custom prompt file
deal-summarize --deal-id 123 --prompt-file prompts/executive-brief.md

# Or with short flag
deal-summarize --deal-id 123 --prompt prompts/executive-brief.md
```

## Available Prompts

### `default.md` - Comprehensive Analysis
The default prompt provides detailed, structured deal analysis suitable for sales teams:
- Detailed stakeholder analysis
- Comprehensive opportunity and risk assessment
- Complete interaction timeline
- Actionable next steps
- **Best for:** Sales reps, account managers, detailed deal reviews

### `executive-brief.md` - Executive Summary
Concise, high-level summaries optimized for executives:
- 2-3 sentence executive summary
- Financial overview and timeline
- Strategic assessment
- Risk level indicator
- Single clear recommendation
- **Maximum 250 words**
- **Best for:** C-level, executives, quick reviews

## Creating Your Own Prompt

### 1. Copy an Existing Prompt

```bash
cd generate_deal_summary/prompts
cp default.md my-custom-prompt.md
```

### 2. Edit the Template

Open your new file and modify the `## System Prompt` section:

```markdown
## System Prompt

You are a [your role description].

Your task is to [your objective].

**Your analysis should:**
1. [Guideline 1]
2. [Guideline 2]

**Output Format:**
[Your desired markdown structure]

**Guidelines:**
[Your specific instructions]
```

### 3. Use Template Variables (Optional)

The system supports Handlebars-style conditional blocks:

```markdown
{{#if with_change_analysis}}
This content only appears when analyzing changes between summaries.
{{/if}}
```

**Available variables:**
- `with_change_analysis` - True when comparing with previous summary

### 4. Test Your Prompt

```bash
deal-summarize --deal-id 123 --prompt your-custom-prompt.md
```

## Template Structure

### Required Sections

Your prompt file must include:

```markdown
## System Prompt

[Your prompt content here]
```

The system extracts text between `## System Prompt` and the next `##` header.

### Optional Sections

You can add documentation sections for contributors:

```markdown
## User Prompt Template

[Document what data will be provided - for reference only]

## Examples

[Show example outputs]

## Customization Notes

[Explain your customization choices]
```

## Prompt Design Tips

### 1. Be Specific About Output Format

```markdown
**Bad:**
Provide a summary of the deal.

**Good:**
Provide your analysis as a Markdown document with these exact sections:
# [Deal Name]
## Executive Summary
[specific requirements]
```

### 2. Set Clear Constraints

```markdown
- Maximum length: 300 words
- Use bullet points for lists
- Include emoji sparingly (✅ ⚠️  📊)
- Focus on [specific aspects]
```

### 3. Define The AI's Role

```markdown
**Bad:**
You are helpful.

**Good:**
You are a senior sales analyst with 15 years of experience in B2B SaaS sales, specializing in enterprise deals over $100k ARR.
```

### 4. Provide Context on Audience

```markdown
**Your summaries will be read by:**
- Technical decision makers
- Procurement teams
- C-level executives with limited time

**Therefore:**
- Avoid sales jargon
- Emphasize ROI and business value
- Be extremely concise
```

## Example Use Cases

### For Different Roles

**Sales Development (SDR):**
- Focus: Lead qualification, discovery questions
- Length: Brief (< 150 words)
- Emphasis: Next touchpoint, BANT qualification

**Account Executive (AE):**
- Focus: Deal progression, objections, stakeholders
- Length: Detailed (300-500 words)
- Emphasis: Closing strategy, competitive landscape

**Customer Success:**
- Focus: Relationship health, expansion opportunities
- Length: Medium (200-300 words)
- Emphasis: Engagement trends, upsell signals

### For Different Deal Types

**Enterprise Deals:**
- Emphasize: Procurement process, legal review, stakeholder mapping
- Include: Decision criteria, evaluation timeline, competitive analysis

**SMB Deals:**
- Emphasize: Quick wins, simplicity, fast time-to-value
- Include: Budget constraints, implementation speed

**Renewal/Upsell:**
- Emphasize: Usage patterns, satisfaction indicators
- Include: Value delivered, expansion opportunities

## Sharing Your Prompts

If you create a useful prompt template:

1. **Test it thoroughly** with various deals
2. **Document the use case** in the file header
3. **Share it** by creating a pull request or sharing the file

## Troubleshooting

### "No '## System Prompt' section found"

Make sure your file includes the exact header:
```markdown
## System Prompt
```
(Two `#` symbols, space, then `System Prompt`)

### Prompt not being used

Check that you're using the correct path:
```bash
# Relative to current directory
--prompt-file prompts/my-prompt.md

# Or absolute path
--prompt-file /full/path/to/my-prompt.md
```

### Output doesn't match expectations

- The AI interprets your prompt, results may vary slightly
- Be more specific in your instructions
- Add examples of desired output format
- Adjust temperature/model if needed

## Advanced Customization

### Multi-Language Prompts

```markdown
## System Prompt

You are a sales analyst. Respond in French.

**Format de sortie:**
# [Nom de l'affaire]
...
```

### Domain-Specific Prompts

```markdown
## System Prompt

You are a pharmaceutical industry sales analyst specializing in clinical trial management software.

**Your analysis must consider:**
- FDA compliance requirements
- HIPAA implications
- Clinical trial phases
...
```

### Sentiment-Focused Analysis

```markdown
## System Prompt

You are an expert in analyzing customer sentiment and engagement signals.

**Focus your analysis on:**
- Tone in communications (enthusiastic, neutral, concerned)
- Response times and frequency
- Engagement level changes over time
...
```

## Contributing

We welcome contributions of new prompt templates! Consider sharing prompts for:
- Different industries (healthcare, finance, manufacturing, etc.)
- Different sales methodologies (MEDDIC, SPIN, Challenger, etc.)
- Different languages
- Specialized use cases

Share via pull request or discussion in the project repository.
