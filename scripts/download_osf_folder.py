"""Download and checksum a public OSF folder recursively.

This utility is intentionally separate from the converter. It creates a JSON
manifest suitable for recording the exact public files used in integration
testing and resumes interrupted downloads through HTTP range requests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath
from typing import Any


def _json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def _list_folder(url: str, prefix: PurePosixPath | None = None) -> list[dict[str, Any]]:
    prefix = PurePosixPath() if prefix is None else prefix
    separator = "&" if "?" in url else "?"
    next_url: str | None = f"{url}{separator}page[size]=100"
    output: list[dict[str, Any]] = []
    while next_url:
        document = _json(next_url)
        for item in document["data"]:
            attributes = item["attributes"]
            relative = prefix / attributes["name"]
            if attributes["kind"] == "folder":
                child = item["relationships"]["files"]["links"]["related"]["href"]
                output.extend(_list_folder(child, relative))
                continue
            hashes = attributes.get("extra", {}).get("hashes", {})
            output.append(
                {
                    "path": relative.as_posix(),
                    "size": int(attributes.get("size") or 0),
                    "sha256": hashes.get("sha256"),
                    "download": item["links"]["download"],
                }
            )
        next_url = document.get("links", {}).get("next")
    return output


def _target(root: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe OSF path {relative!r}")
    return root.joinpath(*path.parts)


def _download(file: dict[str, Any], destination: Path) -> None:
    target = _target(destination, file["path"])
    target.parent.mkdir(parents=True, exist_ok=True)
    expected_size = file["size"]
    if target.exists() and target.stat().st_size == expected_size:
        return

    partial = target.with_name(f"{target.name}.part")
    offset = partial.stat().st_size if partial.exists() else 0
    request = urllib.request.Request(file["download"])
    if offset:
        request.add_header("Range", f"bytes={offset}-")
    with urllib.request.urlopen(request, timeout=120) as response:
        append = offset > 0 and response.status == 206
        mode = "ab" if append else "wb"
        with partial.open(mode) as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
    if partial.stat().st_size != expected_size:
        raise OSError(
            f"Size mismatch for {file['path']}: "
            f"expected {expected_size}, got {partial.stat().st_size}"
        )
    os.replace(partial, target)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _download_and_verify(file: dict[str, Any], destination: Path) -> str:
    _download(file, destination)
    actual_hash = _sha256(_target(destination, file["path"]))
    expected_hash = file["sha256"]
    if expected_hash is not None and actual_hash != expected_hash:
        raise OSError(f"SHA-256 mismatch for {file['path']}")
    return actual_hash


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("endpoint", help="OSF folder API endpoint")
    parser.add_argument("destination", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--inventory-only", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)

    files = _list_folder(args.endpoint)
    total = sum(file["size"] for file in files)
    print(f"Discovered {len(files)} files ({total} bytes)", flush=True)
    if not args.inventory_only:
        if args.workers < 1:
            parser.error("--workers must be at least 1")
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(_download_and_verify, file, args.destination): file
                for file in files
            }
            for index, future in enumerate(as_completed(futures), start=1):
                file = futures[future]
                file["verified_sha256"] = future.result()
                print(f"[{index}/{len(files)}] {file['path']}", flush=True)

    manifest = {
        "schema_version": 1,
        "osf_api_endpoint": args.endpoint,
        "file_count": len(files),
        "total_bytes": total,
        "downloaded_and_verified": not args.inventory_only,
        "files": files,
    }
    if args.manifest is not None:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    else:
        json.dump(manifest, sys.stdout, indent=2)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
