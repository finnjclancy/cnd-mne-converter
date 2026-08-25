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


def _outcome(subject: dict[str, Any], report: dict[str, Any]) -> str:
    """Return schema-v3 outcome, inferring it for historical schema-v2 reports."""
    if "outcome" in subject:
        return str(subject["outcome"])
    if subject.get("failure"):
        return (
            "source_read_failure"
            if not subject.get("mne_created")
            else "conversion_failure"
        )
    if subject.get("validation_errors"):
        return "validation_failure"
    if subject.get("n_neural_samples", 0) == 0:
        return "empty_neural_data"
    if report.get("neural_unit_assumption") is None:
        return "structural_pass"
    checks = (
        subject.get("mne_created")
        and subject.get("mne_shape_verified")
        and subject.get("stimulus_mne_views_verified") is not False
        and (
            not report.get("round_trip_requested") or subject.get("round_trip_verified")
        )
        and (
            not report.get("mne_smoke_test_requested")
            or subject.get("mne_psd_finite") is True
        )
    )
    return "complete_pass" if checks else "verification_failure"


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
        outcomes = Counter(_outcome(subject, report) for subject in report["subjects"])
        failures = sum(
            count
            for outcome, count in outcomes.items()
            if outcome not in {"complete_pass", "structural_pass", "empty_neural_data"}
        )
        scalar_values = sum(
            subject["n_neural_samples"] * subject["n_channels"]
            for subject in report["subjects"]
        )
        datasets.append(
            {
                "dataset": report["dataset_name"],
                "report": path.name,
                "passed": failures == 0,
                "subject_files": summary["n_subjects"],
                "complete_passes": outcomes["complete_pass"],
                "empty_neural_files": outcomes["empty_neural_data"],
                "failed_subject_files": failures,
                "outcome_counts": dict(sorted(outcomes.items())),
                "trials": summary["n_trials"],
                "neural_samples": summary["n_neural_samples"],
                "scalar_neural_values": scalar_values,
            }
        )
    output = {
        "schema_version": 2,
        "report_count": len(datasets),
        "dataset_reports": datasets,
        "totals": {
            "subject_files": sum(item["subject_files"] for item in datasets),
            "passed_subject_files": sum(item["complete_passes"] for item in datasets),
            "empty_neural_files": sum(item["empty_neural_files"] for item in datasets),
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
