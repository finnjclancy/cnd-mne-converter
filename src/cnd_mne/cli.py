"""Command-line interface for inspecting CND files."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .inspection import inspect_cnd
from .io import read_cnd


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cnd-mne")
    commands = parser.add_subparsers(dest="command", required=True)

    inspect_parser = commands.add_parser("inspect", help="inspect and validate CND")
    inspect_parser.add_argument(
        "path", help="CND directory or subject/stimulus .mat file"
    )
    inspect_parser.add_argument("--stimulus-path")
    inspect_parser.add_argument("--subject")
    inspect_parser.add_argument(
        "--no-stimulus", action="store_true", help="do not infer a stimulus file"
    )

    args = parser.parse_args(argv)
    if args.command == "inspect":
        recording = read_cnd(
            args.path,
            stimulus_path=args.stimulus_path,
            subject=args.subject,
            load_stimulus=not args.no_stimulus,
        )
        print(json.dumps(inspect_cnd(recording), indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
