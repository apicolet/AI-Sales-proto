"""
Setup configuration for Sales Engagement Action (Script 3)
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text(encoding="utf-8")

setup(
    name="sales-engagement-action",
    version="0.1.0",
    description="AI-powered sales engagement action recommendations with learning feedback loop",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="DTSL",
    python_requires=">=3.9",
    packages=find_packages(),
    install_requires=[
        "anthropic>=0.39.0",
        "pydantic>=2.0.0",
        "typer>=0.9.0",
        "rich>=13.0.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "pyyaml>=6.0",
        "python-dateutil>=2.8.0",
    ],
    entry_points={
        "console_scripts": [
            "sales-action=sales_engagement_action.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    package_data={
        "sales_engagement_action": ["prompts/*.md"],
    },
    include_package_data=True,
)
