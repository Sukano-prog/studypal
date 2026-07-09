#!/usr/bin/env python3
"""
StudyPal - Advanced Study Assistant
Setup script for installation and distribution
"""

from setuptools import setup, find_packages
import os
import re

# Read version from config.py
with open(os.path.join("src", "config.py"), "r", encoding="utf-8") as f:
    content = f.read()
    version_match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
    if version_match:
        VERSION = version_match.group(1)
    else:
        VERSION = "3.0.1"

# Read long description from README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="studypal",
    version=VERSION,
    author="Your Name",
    author_email="your.email@example.com",
    description="Advanced Study Assistant with Text-to-Speech",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/studypal",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Topic :: Education",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "PySide6>=6.6.0",
        "numpy>=1.24.0",
        "sounddevice>=0.4.6",
        "soundfile>=0.12.1",
        "pypdf>=3.15.0",
        "python-docx>=1.1.0",
        "pyttsx3>=2.90",
        "gtts>=2.4.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "isort>=5.10.0",
            "flake8>=4.0.0",
            "pylint>=2.10.0",
            "pyinstaller>=5.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "studypal=main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
