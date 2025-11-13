"""
Setup configuration for Brevo Data Gatherer (Script 1)
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text(encoding="utf-8")

setup(
    name="brevo-data-gatherer",
    version="1.0.0",
    description="Non-AI data enrichment tool for Brevo CRM with multi-source integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="DTSL",
    author_email="tech@brevo.com",
    url="https://github.com/DTSL/brevo-sales-ai-agent",
    python_requires=">=3.9",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.0.0",
        "requests>=2.31.0",
        "PyYAML>=6.0.0",
        "typer>=0.9.0",
        "rich>=13.0.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "brevo-enrich=brevo_data_gatherer.cli:main",
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
        "brevo_data_gatherer": ["cache/schema.sql"],
    },
    include_package_data=True,
)
