#!/usr/bin/env python3
"""
Zora Trading Bot package setup
"""
from setuptools import setup, find_packages

setup(
    name="zora-portia-bot",
    version="0.1.0",
    description="Trading bot for Zora Network with Portia AI integration",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.8.3",
        "numpy>=1.23.5",
        "python-dotenv>=0.21.0",
        "pydantic>=1.10.2",
        "websockets>=10.4",
        "pandas>=1.5.2",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "zora-bot=run_bot:main",
        ],
    },
)
