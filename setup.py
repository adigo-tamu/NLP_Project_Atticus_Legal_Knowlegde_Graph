"""Setup script for Project Atticus."""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="project-atticus",
    version="1.0.0",
    author="Aditya Gollamudi",
    author_email="",
    description="LLM-driven Legal Knowledge Graph Construction System",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/project-atticus",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "atticus=atticus.cli:main",
        ],
    },
    include_package_data=True,
)
