"""Reproducible end-to-end verification for local CND datasets."""

from __future__ import annotations

import platform
import time
import warnings
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import mne
import numpy as np

from .io import read_cnd
from .mne import _unit_scale, to_mne
from .model import CNDRecording
from .validation import ValidationIssue, validate_cnd


@dataclass(slots=True, frozen=True)
class SubjectVerification:
    """Verification evidence for one CND subject file."""

    subject: str
    neural_file: str
    stimulus_file: str | None
    n_trials: int
    n_channels: int
    n_neural_samples: int
    neural_sfreq: float
    stimulus_sfreq: float | None
    n_stimulus_features: int
    warning_counts: dict[str, int]
    validation_errors: tuple[dict[str, str], ...]
    max_duration_difference_seconds: float | None
    mne_created: bool
    mne_shape_verified: bool
    mne_max_abs_error_source_units: float | None
    stimulus_mne_views_verified: bool | None
    mne_psd_finite: bool | None
    round_trip_verified: bool
    round_trip_max_abs_error_source_units: float | None
    cnd_metadata_preserved: bool | None
    conversion_warnings: tuple[str, ...]
    failure: str | None
    elapsed_seconds: float


@dataclass(slots=True, frozen=True)
class DatasetVerification:
    """Serializable verification report for a complete CND dataset."""

    schema_version: int
    dataset_name: str
    dataset_path: str
    generated_at_utc: str
    versions: dict[str, str]
    neural_unit_assumption: str | None
    strict_spec: bool
    round_trip_requested: bool
    mne_smoke_test_requested: bool
    subjects: tuple[SubjectVerification, ...]

    @property
    def passed(self) -> bool:
        """Whether every subject passed all requested checks."""
        return all(
            not subject.validation_errors
            and subject.failure is None
            and (
                self.neural_unit_assumption is None
                or (
                    subject.mne_created
                    and subject.mne_shape_verified
                    and subject.stimulus_mne_views_verified is not False
                    and (not self.round_trip_requested or subject.round_trip_verified)
                    and (
                        not self.mne_smoke_test_requested
                        or subject.mne_psd_finite is True
                    )
                )
            )
            for subject in self.subjects
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable report including aggregate totals."""
        result = asdict(self)
        warning_counts = Counter(
            {
                code: sum(
                    subject.warning_counts.get(code, 0) for subject in self.subjects
                )
                for code in {
                    code for subject in self.subjects for code in subject.warning_counts
                }
            }
        )
        max_mne_error = _optional_max(
            subject.mne_max_abs_error_source_units for subject in self.subjects
        )
        max_round_trip_error = _optional_max(
            subject.round_trip_max_abs_error_source_units for subject in self.subjects
        )
        result["summary"] = {
            "passed": self.passed,
            "n_subjects": len(self.subjects),
            "n_failed_subjects": sum(
                subject.failure is not None or bool(subject.validation_errors)
                for subject in self.subjects
            ),
            "n_trials": sum(subject.n_trials for subject in self.subjects),
            "n_neural_samples": sum(
                subject.n_neural_samples for subject in self.subjects
            ),
            "warning_counts": dict(sorted(warning_counts.items())),
            "max_mne_abs_error_source_units": max_mne_error,
            "max_round_trip_abs_error_source_units": max_round_trip_error,
        }
        return result


def verify_dataset(
    path: str | Path,
    *,
    dataset_name: str | None = None,
    neural_unit: str | None = None,
    strict_spec: bool = False,
    round_trip: bool = True,
    mne_smoke_test: bool = True,
) -> DatasetVerification:
    """Verify every ``dataSub*.mat`` file in a local CND dataset.

    ``neural_unit`` is an explicit testing assumption for legacy datasets. It
    is recorded in the report and is never inferred. When omitted, parsing and
    validation run but MNE and round-trip checks are skipped.
    """
    supplied_path = Path(path).expanduser()
    source = supplied_path.resolve()
    data_directory = source / "dataCND" if (source / "dataCND").is_dir() else source
    files = sorted(data_directory.glob("dataSub*.mat"), key=_subject_sort_key)
    if not files:
        raise FileNotFoundError(f"No dataSub*.mat files found in {data_directory}")
    if neural_unit is not None:
        _unit_scale(neural_unit)

    subjects = tuple(
        _verify_subject(
            source,
            file,
            neural_unit=neural_unit,
            strict_spec=strict_spec,
            round_trip=round_trip,
            mne_smoke_test=mne_smoke_test,
        )
        for file in files
    )
    return DatasetVerification(
        schema_version=1,
        dataset_name=dataset_name or source.name,
        dataset_path=str(supplied_path),
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        versions={
            "cnd_mne": _package_version(),
            "mne": mne.__version__,
            "numpy": np.__version__,
            "python": platform.python_version(),
        },
        neural_unit_assumption=neural_unit,
        strict_spec=strict_spec,
        round_trip_requested=round_trip and neural_unit is not None,
        mne_smoke_test_requested=mne_smoke_test and neural_unit is not None,
        subjects=subjects,
    )


def _verify_subject(
    dataset_path: Path,
    neural_file: Path,
    *,
    neural_unit: str | None,
    strict_spec: bool,
    round_trip: bool,
    mne_smoke_test: bool,
) -> SubjectVerification:
    started = time.monotonic()
    subject = neural_file.stem.removeprefix("dataSub")
    empty: dict[str, Any] = {
        "subject": subject,
        "neural_file": neural_file.name,
        "stimulus_file": None,
        "n_trials": 0,
        "n_channels": 0,
        "n_neural_samples": 0,
        "neural_sfreq": 0.0,
        "stimulus_sfreq": None,
        "n_stimulus_features": 0,
        "warning_counts": {},
        "validation_errors": (),
        "max_duration_difference_seconds": None,
        "mne_created": False,
        "mne_shape_verified": False,
        "mne_max_abs_error_source_units": None,
        "stimulus_mne_views_verified": None,
        "mne_psd_finite": None,
        "round_trip_verified": False,
        "round_trip_max_abs_error_source_units": None,
        "cnd_metadata_preserved": None,
        "conversion_warnings": (),
        "failure": None,
    }
    try:
        recording = read_cnd(dataset_path, subject=subject)
        report = validate_cnd(recording, strict_spec=strict_spec)
        neural = recording.neural
        stimulus = recording.stimulus
        assert neural is not None
        empty.update(
            {
                "stimulus_file": (
                    stimulus.source_path.name
                    if stimulus is not None and stimulus.source_path is not None
                    else None
                ),
                "n_trials": neural.n_trials,
                "n_channels": neural.n_channels,
                "n_neural_samples": sum(
                    np.asarray(trial).shape[0] for trial in neural.trials
                ),
                "neural_sfreq": neural.sfreq,
                "stimulus_sfreq": stimulus.sfreq if stimulus is not None else None,
                "n_stimulus_features": (
                    stimulus.n_features if stimulus is not None else 0
                ),
                "warning_counts": dict(
                    sorted(Counter(issue.code for issue in report.warnings).items())
                ),
                "validation_errors": tuple(
                    _issue_dict(issue) for issue in report.errors
                ),
                "max_duration_difference_seconds": _max_duration_difference(recording),
            }
        )
        if report.errors or neural_unit is None:
            return SubjectVerification(
                **empty, elapsed_seconds=round(time.monotonic() - started, 6)
            )

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            converted = to_mne(recording, neural_unit=neural_unit)
        scale = _unit_scale(neural_unit)
        shape_verified = True
        mne_error = 0.0
        for source_trial, raw in zip(neural.trials, converted.raws, strict=True):
            expected = np.asarray(source_trial)
            actual_source_units = raw.get_data().T / scale
            shape_verified &= actual_source_units.shape == expected.shape
            if actual_source_units.shape == expected.shape:
                mne_error = max(
                    mne_error, _max_abs_error(expected, actual_source_units)
                )

        psd_finite = None
        if mne_smoke_test:
            psd_finite = _mne_psd_is_finite(converted.raws[0])

        stimulus_views_verified = None
        if stimulus is not None:
            stimulus_views_verified = True
            for feature_index, feature_trials in enumerate(stimulus.features):
                stimulus_raws = converted.stimulus_raws(feature_index)
                stimulus_views_verified &= len(stimulus_raws) == len(feature_trials)
                for source_trial, raw in zip(
                    feature_trials, stimulus_raws, strict=True
                ):
                    expected = np.asarray(source_trial)
                    if expected.ndim == 1:
                        expected = expected[:, np.newaxis]
                    stimulus_views_verified &= raw.get_data().shape == expected.T.shape
                    if raw.get_data().shape == expected.T.shape:
                        stimulus_views_verified &= np.array_equal(
                            raw.get_data(), expected.T
                        )

        round_trip_verified = False
        round_trip_error = None
        metadata_preserved = None
        if round_trip:
            converted_back = converted.to_cnd(on_unsupported_metadata="raise")
            assert converted_back.neural is not None
            round_trip_error = max(
                _max_abs_error(before, after)
                for before, after in zip(
                    neural.trials, converted_back.neural.trials, strict=True
                )
            )
            metadata_preserved = (
                converted_back.stimulus is recording.stimulus
                and converted_back.neural.extra_fields is neural.extra_fields
                and converted_back.neural.external_fields is neural.external_fields
                and converted_back.neural.channel_locations is neural.channel_locations
                and converted_back.neural.original_trial_positions
                == neural.original_trial_positions
            )
            numerically_equivalent = all(
                np.allclose(before, after, rtol=1e-12, atol=1e-12)
                for before, after in zip(
                    neural.trials, converted_back.neural.trials, strict=True
                )
            )
            round_trip_verified = numerically_equivalent and metadata_preserved

        empty.update(
            {
                "mne_created": True,
                "mne_shape_verified": shape_verified,
                "mne_max_abs_error_source_units": mne_error,
                "stimulus_mne_views_verified": stimulus_views_verified,
                "mne_psd_finite": psd_finite,
                "round_trip_verified": round_trip_verified,
                "round_trip_max_abs_error_source_units": round_trip_error,
                "cnd_metadata_preserved": metadata_preserved,
                "conversion_warnings": tuple(str(item.message) for item in caught),
            }
        )
    except Exception as error:  # report each subject without aborting the matrix
        empty["failure"] = f"{type(error).__name__}: {error}"
    return SubjectVerification(
        **empty, elapsed_seconds=round(time.monotonic() - started, 6)
    )


def _mne_psd_is_finite(raw: mne.io.BaseRaw) -> bool:
    duration = min(10.0, raw.times[-1])
    segment = raw.copy().crop(tmin=0.0, tmax=duration).pick([0])
    n_fft = min(1024, segment.n_times)
    if n_fft < 2:
        return False
    nyquist = float(segment.info["sfreq"]) / 2
    spectrum = segment.compute_psd(
        method="welch",
        fmin=0.0,
        fmax=nyquist,
        n_fft=n_fft,
        verbose="ERROR",
    )
    return bool(np.isfinite(spectrum.get_data()).all())


def _max_duration_difference(recording: CNDRecording) -> float | None:
    differences = [
        abs(metadata.neural_duration_seconds - metadata.stimulus_duration_seconds)
        for metadata in recording.trial_metadata
        if metadata.neural_duration_seconds is not None
        and metadata.stimulus_duration_seconds is not None
    ]
    return max(differences) if differences else None


def _max_abs_error(expected: Any, actual: Any) -> float:
    difference = np.abs(
        np.asarray(expected, dtype=np.float64) - np.asarray(actual, dtype=np.float64)
    )
    return float(np.max(difference, initial=0.0))


def _issue_dict(issue: ValidationIssue) -> dict[str, str]:
    return {"code": issue.code, "path": issue.path, "message": issue.message}


def _subject_sort_key(path: Path) -> tuple[int, str]:
    label = path.stem.removeprefix("dataSub")
    return (int(label), label) if label.isdigit() else (2**31 - 1, label)


def _optional_max(values: Any) -> float | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _package_version() -> str:
    try:
        return version("cnd-mne-converter")
    except PackageNotFoundError:
        return "unknown"
