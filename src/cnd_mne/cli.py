"""Command-line interface for inspecting CND files."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .inspection import inspect_cnd
from .io import read_cnd
from .verification import verify_dataset


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
    inspect_parser.add_argument(
        "--strict-spec",
        action="store_true",
        help="treat CND 1.0 conformance deviations as errors",
    )

    verify_parser = commands.add_parser(
        "verify-dataset", help="verify every subject and exercise MNE end to end"
    )
    verify_parser.add_argument("path", help="dataset root or dataCND directory")
    verify_parser.add_argument("--dataset-name")
    verify_parser.add_argument(
        "--neural-unit",
        help="explicit source neural unit for MNE checks (for example uV or uM)",
    )
    verify_parser.add_argument(
        "--strict-spec",
        action="store_true",
        help="treat CND 1.0 conformance deviations as errors",
    )
    verify_parser.add_argument(
        "--no-round-trip", action="store_true", help="skip MNE-to-CND round trip"
    )
    verify_parser.add_argument(
        "--serialized-round-trip",
        action="store_true",
        help="also write and reread temporary MATLAB files (slower)",
    )
    verify_parser.add_argument(
        "--mat-version",
        choices=("5", "7.3"),
        default="5",
        help="MATLAB format used by --serialized-round-trip (default: 5)",
    )
    verify_parser.add_argument(
        "--no-mne-smoke",
        action="store_true",
        help="skip the MNE Welch PSD smoke test",
    )
    verify_parser.add_argument(
        "--output", type=Path, help="write the JSON report to this file"
    )

    args = parser.parse_args(argv)
    if args.command == "inspect":
        recording = read_cnd(
            args.path,
            stimulus_path=args.stimulus_path,
            subject=args.subject,
            load_stimulus=not args.no_stimulus,
        )
        print(
            json.dumps(inspect_cnd(recording, strict_spec=args.strict_spec), indent=2)
        )
        return 0
    if args.command == "verify-dataset":
        report = verify_dataset(
            args.path,
            dataset_name=args.dataset_name,
            neural_unit=args.neural_unit,
            strict_spec=args.strict_spec,
            round_trip=not args.no_round_trip,
            serialized_round_trip=args.serialized_round_trip,
            serialized_mat_version=args.mat_version,
            mne_smoke_test=not args.no_mne_smoke,
        )
        payload = json.dumps(report.to_dict(), indent=2) + "\n"
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
        print(payload, end="")
        return 0 if report.passed else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
