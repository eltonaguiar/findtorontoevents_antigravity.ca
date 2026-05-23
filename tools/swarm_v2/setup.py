from setuptools import setup, find_packages

setup(
    name="swarms",
    version="2.0.0",
    description="Multi-agent swarm system for coding, PR review, CI monitoring, research, and ensemble decision-making",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "pydantic>=2.0",
        "chromadb>=0.5.0",
        "sentence-transformers>=3.0",
        "numpy>=1.26",
        "click>=8.0",
        "aiohttp>=3.9",
        "requests>=2.31",
        "PyYAML>=6.0",
        "rank-bm25>=0.2.2",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0",
            "pytest-asyncio>=0.23",
            "pytest-cov>=5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "swarm=swarms.cli.main:cli",
        ],
    },
)
