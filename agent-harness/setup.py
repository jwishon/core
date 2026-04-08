"""Setup for cli-anything-homeassistant PyPI package."""

from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-homeassistant",
    version="0.1.0",
    description="CLI harness for Home Assistant — control entities, call services, render templates, query history",
    long_description_content_type="text/markdown",
    author="cli-anything",
    python_requires=">=3.10",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    install_requires=[
        "click>=8.0",
        "requests>=2.28",
    ],
    extras_require={
        "dev": ["pytest>=7.0", "pytest-mock>=3.0"],
    },
    entry_points={
        "console_scripts": [
            "cli-anything-homeassistant=cli_anything.homeassistant.homeassistant_cli:main",
            "cli-anything-ha=cli_anything.homeassistant.homeassistant_cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Topic :: Home Automation",
        "Topic :: Utilities",
    ],
)
