"""Resume a large public file with parallel, verified HTTP byte ranges."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def _ranges(start: int, stop: int, count: int) -> list[tuple[int, int]]:
    length = stop - start
    return [
        (start + length * index // count, start + length * (index + 1) // count - 1)
        for index in range(count)
        if start + length * index // count < start + length * (index + 1) // count
    ]


def _download_range(
    url: str, destination: Path, start: int, end: int
) -> tuple[int, int, Path]:
    part = destination.with_name(f".{destination.name}.{start}-{end}.part")
    expected = end - start + 1
    for attempt in range(1, 11):
        offset = part.stat().st_size if part.exists() else 0
        if offset == expected:
            return start, end, part
        if offset > expected:
            part.unlink()
            offset = 0
        request_start = start + offset
        request = urllib.request.Request(url)
        request.add_header("Range", f"bytes={request_start}-{end}")
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                if response.status != 206:
                    raise OSError(f"Server ignored byte range: HTTP {response.status}")
                content_range = response.headers.get("Content-Range", "")
                if not content_range.startswith(f"bytes {request_start}-{end}/"):
                    raise OSError(f"Unexpected Content-Range {content_range!r}")
                with part.open("ab") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
        except (OSError, urllib.error.URLError):
            if attempt == 10:
                raise
            time.sleep(attempt)
    if part.stat().st_size != expected:
        raise OSError(f"Range {start}-{end} has the wrong size")
    return start, end, part


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("destination", type=Path)
    parser.add_argument("total_bytes", type=int)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    prefix_size = args.destination.stat().st_size if args.destination.exists() else 0
    if prefix_size > args.total_bytes:
        raise OSError("Existing file exceeds expected size")
    if prefix_size == args.total_bytes:
        print(f"Already complete; sha256={_sha256(args.destination)}")
        return 0

    ranges = _ranges(prefix_size, args.total_bytes, args.workers)
    completed: list[tuple[int, int, Path]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(_download_range, args.url, args.destination, start, end): (
                start,
                end,
            )
            for start, end in ranges
        }
        for future in as_completed(futures):
            result = future.result()
            completed.append(result)
            print(f"Downloaded bytes {result[0]}-{result[1]}", flush=True)

    temporary = args.destination.with_name(f".{args.destination.name}.complete")
    temporary.unlink(missing_ok=True)
    with temporary.open("wb") as output:
        if prefix_size:
            with args.destination.open("rb") as prefix:
                shutil.copyfileobj(prefix, output, length=1024 * 1024)
        for start, end, part in sorted(completed):
            if part.stat().st_size != end - start + 1:
                raise OSError(f"Range part {part} has the wrong size")
            with part.open("rb") as source:
                shutil.copyfileobj(source, output, length=1024 * 1024)
    if temporary.stat().st_size != args.total_bytes:
        raise OSError("Assembled file has the wrong size")
    os.replace(temporary, args.destination)
    for _, _, part in completed:
        part.unlink()
    print(
        f"Complete: {args.destination} ({args.total_bytes} bytes); "
        f"sha256={_sha256(args.destination)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
