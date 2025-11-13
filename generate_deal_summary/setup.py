"""
Setup configuration for Generate Deal Summary (Script 2)
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text(encoding="utf-8")

setup(
    name="generate-deal-summary",
    version="1.0.0",
    description="AI-powered deal summarization using enriched Brevo CRM data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="DTSL",
    python_requires=">=3.9",
    packages=find_packages(),
    install_requires=[
        "anthropic>=0.18.0",
        "pydantic>=2.0.0",
        "typer>=0.9.0",
        "rich>=13.0.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "deal-summarize=generate_deal_summary.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
