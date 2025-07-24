"""Setup configuration for DMS"""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

# Read requirements, separating main and dev dependencies
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if not os.path.exists(requirements_path):
        return []
    
    with open(requirements_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    requirements = []
    dev_requirements = []
    in_dev_section = False
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            if "Development dependencies" in line:
                in_dev_section = True
            continue
        
        if in_dev_section:
            dev_requirements.append(line)
        else:
            requirements.append(line)
    
    return requirements, dev_requirements

# Get version from package
def get_version():
    version_file = os.path.join(os.path.dirname(__file__), "dms", "__init__.py")
    if os.path.exists(version_file):
        with open(version_file, "r") as f:
            for line in f:
                if line.startswith("__version__"):
                    return line.split("=")[1].strip().strip('"').strip("'")
    return "0.1.0"

requirements, dev_requirements = read_requirements()

setup(
    name="dms",
    version=get_version(),
    description="Document Management System - RAG-powered PDF search and query tool",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="DMS Team",
    author_email="dms@example.com",
    url="https://github.com/rmoriz/dms",
    project_urls={
        "Bug Reports": "https://github.com/rmoriz/dms/issues",
        "Source": "https://github.com/rmoriz/dms",
        "Documentation": "https://github.com/rmoriz/dms#readme",
    },
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
        "test": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "dms=dms.cli.main:cli_main",
        ],
    },
    python_requires=">=3.9",
    keywords="pdf, document, search, rag, ai, nlp, ocr, cli",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Office/Business :: Office Suites",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Text Processing :: Indexing",
        "Topic :: Utilities",
    ],
    zip_safe=False,
)