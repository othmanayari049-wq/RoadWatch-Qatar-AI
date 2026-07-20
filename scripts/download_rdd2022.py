#!/usr/bin/env python3
"""List or download official RDD2022 files from the Figshare API."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ARTICLE_ID = "21431547"
ARTICLE_API = f"https://api.figshare.com/v2/articles/{ARTICLE_ID}"


def article_metadata() -> dict[str, Any]:
    request = urllib.request.Request(  # noqa: S310 - fixed official HTTPS endpoint
        ARTICLE_API, headers={"User-Agent": "RoadWatch-Qatar-AI/0.1"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        return json.load(response)


def checksum(path: Path, algorithm: str = "md5") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, destination: Path, expected_md5: str) -> None:
    parsed = urlparse(url)
    allowed_hosts = {"figshare.com", "api.figshare.com", "ndownloader.figshare.com"}
    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        raise ValueError("Figshare returned an untrusted download URL")
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(  # noqa: S310 - URL scheme and host validated above
        url, headers={"User-Agent": "RoadWatch-Qatar-AI/0.1"}
    )
    with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as output:  # noqa: S310
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    if checksum(partial) != expected_md5:
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"Checksum verification failed for {destination.name}")
    partial.replace(destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/raw/rdd2022"))
    parser.add_argument("--match", action="append", default=[], help="Filename substring filter")
    parser.add_argument("--list", action="store_true", help="List files without downloading")
    args = parser.parse_args()

    metadata = article_metadata()
    files = metadata.get("files", [])
    selected = [
        item
        for item in files
        if not args.match or any(value.lower() in item["name"].lower() for value in args.match)
    ]
    if not selected:
        sys.exit("No Figshare files matched the requested filters")

    for item in selected:
        size_gb = item["size"] / (1024**3)
        print(f"{item['name']}: {size_gb:.2f} GB")
        if not args.list:
            destination = args.output / item["name"]
            if destination.is_file() and checksum(destination) == item["computed_md5"]:
                print("  already downloaded and verified")
                continue
            download_file(item["download_url"], destination, item["computed_md5"])
            print("  downloaded and verified")


if __name__ == "__main__":
    main()
