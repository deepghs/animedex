"""Packaging configuration for animedex."""

import os
import re

from setuptools import find_packages, setup

_MODULE_NAME = "animedex"
_PACKAGE_NAME = "animedex"

here = os.path.abspath(os.path.dirname(__file__))


def _read_meta(meta_path):
    """Parse string constants like ``__VERSION__: str = "0.0.1"`` from
    ``animedex/config/meta.py`` without importing the package, so that
    ``setup.py`` can be executed before the package's runtime
    dependencies are installed."""
    with open(meta_path, "r", encoding="utf-8") as fh:
        text = fh.read()
    pattern = re.compile(
        r"^(__[A-Z_]+__)\s*:\s*str\s*=\s*\(?\s*((?:[\"'][^\"']*[\"']\s*)+)\s*\)?",
        re.MULTILINE,
    )
    out = {}
    for name, value_block in pattern.findall(text):
        joined = "".join(re.findall(r"[\"']([^\"']*)[\"']", value_block))
        out[name] = joined
    return out


meta = _read_meta(os.path.join(here, _MODULE_NAME, "config", "meta.py"))


def _load_req(file: str):
    with open(file, "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh.readlines() if line.strip()]


requirements = _load_req("requirements.txt")

_REQ_PATTERN = re.compile(r"^requirements-(\w+)\.txt$")
_REQ_BLACKLIST = {"build"}
group_requirements = {
    item.group(1): _load_req(item.group(0))
    for item in [_REQ_PATTERN.fullmatch(reqpath) for reqpath in os.listdir()]
    if item
    if item.group(1) not in _REQ_BLACKLIST
}

with open("README.md", "r", encoding="utf-8") as fh:
    readme = fh.read()

setup(
    name=_PACKAGE_NAME,
    version=meta["__VERSION__"],
    packages=find_packages(include=(_MODULE_NAME, "%s.*" % _MODULE_NAME)),
    package_data={
        package_name: ["*.yaml", "*.yml", "*.json"]
        for package_name in find_packages(include=("*",))
    },
    description=meta["__DESCRIPTION__"],
    long_description=readme,
    long_description_content_type="text/markdown",
    author=meta["__AUTHOR__"],
    author_email=meta["__AUTHOR_EMAIL__"],
    license="Apache License, Version 2.0",
    keywords=(
        "anime, manga, cli, anilist, mal, jikan, kitsu, mangadex, "
        "trace.moe, danbooru, shikimori, anidb, llm-tools"
    ),
    url="https://github.com/deepghs/animedex",
    python_requires=">=3.7",
    install_requires=requirements,
    extras_require=group_requirements,
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Multimedia",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
        "Typing :: Typed",
        "Natural Language :: English",
    ],
    entry_points={
        "console_scripts": [
            "animedex=animedex.entry:animedex_cli",
        ],
    },
    project_urls={
        "Homepage": "https://github.com/deepghs/animedex",
        "Source": "https://github.com/deepghs/animedex",
        "Bug Reports": "https://github.com/deepghs/animedex/issues",
        "CI": "https://github.com/deepghs/animedex/actions",
        "License": "https://github.com/deepghs/animedex/blob/main/LICENSE",
    },
)
