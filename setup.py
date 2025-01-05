from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="tiktalk",
    version="0.1.0",
    author="JimEverest",
    author_email="your.email@example.com",
    description="A sophisticated desktop application for capturing and analyzing live captions with AI assistance",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/JimEverest/TikTalk",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        "TikTalk": ["config.ini"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Office/Business :: Office Suites",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.8",
    install_requires=[
        "uiautomation>=2.0.20",
        "pyperclip>=1.8.2",
        "tkhtmlview>=0.1.0",
        "markdown>=3.4.0",
        "pywin32>=305",
        "tkinterweb>=3.23.4",
        "configparser>=5.0.0",
        "requests>=2.25.0",
    ],
    entry_points={
        "console_scripts": [
            "tiktalk=TikTalk.capture:main",
        ],
    },
) 