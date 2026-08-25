"""Aggregate committed full-dataset verification reports."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _load_reports(directory: Path) -> list[tuple[Path, dict[str, Any]]]:
    reports = []
    for path in sorted(directory.glob("*.json")):
        if path.name == "catalog-summary.json":
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        if "subjects" in report and "summary" in report:
            reports.append((path, report))
    return reports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    reports = _load_reports(args.reports)
    warnings: Counter[str] = Counter()
    datasets: list[dict[str, Any]] = []
    for path, report in reports:
        summary = report["summary"]
        warnings.update(summary["warning_counts"])
        scalar_values = sum(
            subject["n_neural_samples"] * subject["n_channels"]
            for subject in report["subjects"]
        )
        datasets.append(
            {
                "dataset": report["dataset_name"],
                "report": path.name,
                "passed": summary["passed"],
                "subject_files": summary["n_subjects"],
                "failed_subject_files": summary["n_failed_subjects"],
                "trials": summary["n_trials"],
                "neural_samples": summary["n_neural_samples"],
                "scalar_neural_values": scalar_values,
            }
        )
    output = {
        "schema_version": 1,
        "report_count": len(datasets),
        "dataset_reports": datasets,
        "totals": {
            "subject_files": sum(item["subject_files"] for item in datasets),
            "passed_subject_files": sum(
                item["subject_files"] - item["failed_subject_files"]
                for item in datasets
            ),
            "failed_subject_files": sum(
                item["failed_subject_files"] for item in datasets
            ),
            "trials": sum(item["trials"] for item in datasets),
            "neural_samples": sum(item["neural_samples"] for item in datasets),
            "scalar_neural_values": sum(
                item["scalar_neural_values"] for item in datasets
            ),
            "warning_counts": dict(sorted(warnings.items())),
        },
    }
    payload = json.dumps(output, indent=2) + "\n"
    if args.output is None:
        print(payload, end="")
    else:
        args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
