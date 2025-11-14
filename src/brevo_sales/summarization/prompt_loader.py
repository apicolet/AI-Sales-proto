"""
Utility for loading and processing prompt templates from Markdown files.
"""
import re
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PromptLoader:
    """Loads and processes prompt templates from Markdown files."""

    @staticmethod
    def load_prompt_file(prompt_file: Path) -> str:
        """
        Load system prompt from a Markdown template file.

        Args:
            prompt_file: Path to the prompt template file

        Returns:
            The system prompt text

        Raises:
            FileNotFoundError: If prompt file doesn't exist
            ValueError: If prompt file is invalid
        """
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        content = prompt_file.read_text(encoding='utf-8')

        # Extract the System Prompt section
        system_prompt = PromptLoader._extract_system_prompt(content)

        if not system_prompt:
            raise ValueError(f"No '## System Prompt' section found in {prompt_file}")

        logger.info(f"Loaded prompt from {prompt_file} ({len(system_prompt)} chars)")

        return system_prompt

    @staticmethod
    def _extract_system_prompt(content: str) -> Optional[str]:
        """
        Extract the System Prompt section from markdown content.

        Looks for content between ## System Prompt and the next ## header.
        """
        # Find the System Prompt section
        match = re.search(
            r'##\s+System Prompt\s*\n(.*?)(?=\n##|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )

        if not match:
            return None

        system_prompt = match.group(1).strip()

        return system_prompt

    @staticmethod
    def process_template_variables(
        prompt: str,
        variables: dict
    ) -> str:
        """
        Process template variables in the prompt.

        Supports basic Handlebars-style conditionals:
        - {{#if variable}}...{{/if}}

        Args:
            prompt: The prompt text with template variables
            variables: Dictionary of variable values

        Returns:
            Processed prompt text
        """
        # Process {{#if variable}}...{{/if}} blocks
        def replace_if_block(match):
            var_name = match.group(1)
            content = match.group(2)

            # Check if variable is truthy
            if variables.get(var_name):
                return content
            else:
                return ""

        # Pattern: {{#if variable}}content{{/if}}
        pattern = r'\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}'
        result = re.sub(pattern, replace_if_block, prompt, flags=re.DOTALL)

        return result

    @staticmethod
    def get_default_prompt_path() -> Path:
        """Get the path to the default prompt file."""
        # Get the summarization module directory
        module_dir = Path(__file__).parent
        return module_dir / "prompts" / "default.md"

    @staticmethod
    def load_default_prompt() -> str:
        """Load the default prompt template."""
        default_path = PromptLoader.get_default_prompt_path()
        return PromptLoader.load_prompt_file(default_path)
