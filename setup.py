"""
Setup configuration for brevo-sales unified package.
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text(encoding="utf-8")

setup(
    name="brevo-sales",
    version="1.0.0",
    description="AI-powered sales engagement suite for Brevo CRM - unified package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="DTSL",
    author_email="tech@brevo.com",
    url="https://github.com/apicolet/AI-Sales-proto",
    project_urls={
        "Bug Tracker": "https://github.com/apicolet/AI-Sales-proto/issues",
        "Documentation": "https://github.com/apicolet/AI-Sales-proto/blob/HEAD/README.md",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        # Core dependencies
        "pydantic>=2.0.0",
        "requests>=2.31.0",
        "PyYAML>=6.0.0",
        "python-dotenv>=1.0.0",

        # CLI dependencies
        "typer>=0.9.0",
        "rich>=13.0.0",

        # AI dependencies
        "anthropic>=0.39.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "brevo-sales=brevo_sales.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    package_data={
        "brevo_sales": [
            "enrichment/schema.sql",
            "summarization/prompts/*.md",
            "recommendations/prompts/*.md",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords=[
        "brevo",
        "crm",
        "data-enrichment",
        "linkedin",
        "web-search",
        "sales",
        "marketing",
        "automation",
        "ai",
        "anthropic",
        "claude"
    ],
)
