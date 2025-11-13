"""
Utility for loading and managing company context from markdown file.
"""
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import re

logger = logging.getLogger(__name__)


class CompanyContextLoader:
    """Loads and manages company context from ~/.brevo_sales_agent/company-context.md"""

    @staticmethod
    def load_context(context_file: Optional[Path] = None) -> Dict[str, Any]:
        """
        Load company context from markdown file.

        Args:
            context_file: Path to context file. If None, uses default location.

        Returns:
            Dict with 'content', 'hash', 'loaded_from', 'sections'
        """
        if context_file is None:
            context_file = Path.home() / ".brevo_sales_agent" / "company-context.md"

        if not context_file.exists():
            logger.warning(f"Company context file not found: {context_file}")
            logger.info("Creating default template")
            CompanyContextLoader.create_default_template(context_file)

        content = context_file.read_text(encoding='utf-8')
        sections = CompanyContextLoader.parse_sections(content)

        return {
            "content": content,
            "hash": hashlib.sha256(content.encode()).hexdigest()[:16],
            "loaded_from": str(context_file),
            "sections": sections,
            "version": CompanyContextLoader._extract_version(content)
        }

    @staticmethod
    def parse_sections(content: str) -> Dict[str, str]:
        """
        Parse markdown into sections.

        Returns:
            Dict mapping section names to content
        """
        sections = {}
        current_section = None
        current_content = []

        for line in content.split('\n'):
            if line.startswith('## '):
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # Start new section
                current_section = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections

    @staticmethod
    def _extract_version(content: str) -> str:
        """Extract version from content."""
        match = re.search(r'\*\*Version\*\*:\s*([0-9.]+)', content)
        if match:
            return match.group(1)
        return "1.0.0"

    @staticmethod
    def update_context(
        context_file: Path,
        section: str,
        new_content: str,
        append: bool = True
    ):
        """
        Update a section in the company context file.

        Args:
            context_file: Path to context file
            section: Section name to update
            new_content: Content to add or replace
            append: If True, append to section. If False, replace section.
        """
        if not context_file.exists():
            raise FileNotFoundError(f"Context file not found: {context_file}")

        content = context_file.read_text(encoding='utf-8')
        sections = CompanyContextLoader.parse_sections(content)

        # Update section
        if section in sections:
            if append:
                sections[section] = sections[section] + "\n" + new_content
            else:
                sections[section] = new_content
        else:
            sections[section] = new_content

        # Rebuild content
        new_full_content = CompanyContextLoader._rebuild_content(content, sections)

        # Increment version
        new_full_content = CompanyContextLoader._increment_version(new_full_content)

        # Write back
        context_file.write_text(new_full_content, encoding='utf-8')
        logger.info(f"Updated section '{section}' in {context_file}")

    @staticmethod
    def _rebuild_content(original: str, sections: Dict[str, str]) -> str:
        """Rebuild markdown from sections while preserving structure."""
        lines = []
        
        # Extract header (everything before first ## section)
        header_lines = []
        for line in original.split('\n'):
            if line.startswith('## '):
                break
            header_lines.append(line)
        
        lines.extend(header_lines)
        lines.append("")  # Blank line after header

        # Add sections
        for section_name, section_content in sections.items():
            lines.append(f"## {section_name}")
            lines.append("")
            lines.append(section_content)
            lines.append("")

        return '\n'.join(lines)

    @staticmethod
    def _increment_version(content: str) -> str:
        """Increment patch version in content."""
        def increment_match(match):
            version = match.group(1)
            parts = version.split('.')
            if len(parts) == 3:
                major, minor, patch = parts
                patch = str(int(patch) + 1)
                return f"**Version**: {major}.{minor}.{patch}"
            return match.group(0)

        return re.sub(
            r'\*\*Version\*\*:\s*([0-9.]+)',
            increment_match,
            content
        )

    @staticmethod
    def create_default_template(context_file: Path):
        """Create a default company context template."""
        context_file.parent.mkdir(parents=True, exist_ok=True)

        template = """# Company Context for Sales Engagement

**Version**: 1.0.0
**Created**: {date}
**Last Updated**: {date}
**Maintained By**: sales-engagement-action agent

This file contains company-specific context for AI-powered sales engagement recommendations.

## Company Overview

**Company Name**: [Your Company Name]
**Mission**: [Your mission statement]
**Value Propositions**:
- Value prop 1
- Value prop 2
- Value prop 3

## Products & Services

### Product 1
- Target market: [segments]
- Key features: [features]
- Pricing: [tiers]

### Product 2
- Target market: [segments]
- Key features: [features]
- Pricing: [tiers]

## Communication Guidelines

### Tone of Voice
- Professional but approachable
- Customer pain points first
- Data-driven claims
- Consultative, not pushy

### Messaging Framework
1. Understand their challenge
2. Present relevant solution
3. Provide proof/evidence
4. Clear call to action

## Sales Playbook

### Enterprise Segment (1000+ employees)
- **Approach**: Multi-stakeholder, long sales cycle
- **Key Messages**: ROI, security, scalability
- **Best Channels**: Email, phone, demos

### Mid-Market Segment (100-1000 employees)
- **Approach**: Decision maker focus
- **Key Messages**: Efficiency, cost savings
- **Best Channels**: Email, phone

### SMB Segment (10-100 employees)
- **Approach**: Quick value demonstration
- **Key Messages**: Easy to use, fast results
- **Best Channels**: Email, self-serve

## Learnings & Instructions

### Email Engagement Learnings
- Keep cold outreach under 200 words
- Reference recent context in subject lines
- Lead with pain points, not features

### Call Strategy Learnings
- Schedule discovery calls for 45 minutes
- Prepare 3-5 discovery questions
- Address objections proactively

### LinkedIn Outreach Learnings
- Personalize connection requests
- Provide value before asking
- Keep messages under 300 characters

### WhatsApp Communication Learnings
- Use for established relationships only
- Keep messages brief and mobile-friendly
- Respect time zones and business hours

### Timing & Scheduling Learnings
- Best email times: Tue-Thu, 10 AM-2 PM
- Best call times: Tue-Thu, 10-11 AM or 4-5 PM
- Avoid Mondays and Fridays for cold outreach

## Resources

### Case Studies
- [Link to case study 1]
- [Link to case study 2]

### Documentation
- [Product documentation]
- [Pricing calculator]

### Competitive Intel
- [Competitor comparison]
- [Battle cards]

---

_This context is automatically updated by the sales-engagement-action agent based on feedback and learnings._
""".format(date=__import__('datetime').datetime.now().strftime('%Y-%m-%d'))

        context_file.write_text(template, encoding='utf-8')
        logger.info(f"Created default company context template at: {context_file}")
