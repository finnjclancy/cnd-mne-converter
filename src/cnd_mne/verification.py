"""Reproducible end-to-end verification for local CND datasets."""

from __future__ import annotations

import platform
import tempfile
import time
import warnings
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Literal

import mne
import numpy as np

from .exceptions import CNDValidationError
from .io import read_cnd, write_cnd
from .mne import _unit_scale, to_mne
from .model import CNDRecording
from .validation import ValidationIssue, validate_cnd


@dataclass(slots=True, frozen=True)
class SubjectVerification:
    """Verification evidence for one CND subject file."""

    subject: str
    outcome: str
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
    external_mne_views_verified: bool | None
    mne_psd_finite: bool | None
    round_trip_verified: bool
    round_trip_max_abs_error_source_units: float | None
    cnd_metadata_preserved: bool | None
    serialized_round_trip_verified: bool | None
    serialized_round_trip_max_abs_error_source_units: float | None
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
    serialized_round_trip_requested: bool
    serialized_mat_version: str | None
    mne_smoke_test_requested: bool
    skipped_empty_files: tuple[str, ...]
    subjects: tuple[SubjectVerification, ...]

    @property
    def passed(self) -> bool:
        """Whether every file avoided a converter or source-read failure.

        A structurally valid file containing zero neural samples is classified
        separately as ``empty_neural_data``. It is not a converter failure,
        although it cannot pass an analysis smoke test.
        """
        return all(
            subject.outcome in {"complete_pass", "structural_pass", "empty_neural_data"}
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
        outcome_counts = Counter(subject.outcome for subject in self.subjects)
        result["summary"] = {
            "passed": self.passed,
            "n_discovered_subject_files": len(self.subjects)
            + len(self.skipped_empty_files),
            "n_skipped_empty_files": len(self.skipped_empty_files),
            "n_subjects": len(self.subjects),
            "n_failed_subjects": sum(
                count
                for outcome, count in outcome_counts.items()
                if outcome
                not in {"complete_pass", "structural_pass", "empty_neural_data"}
            ),
            "n_empty_neural_files": outcome_counts["empty_neural_data"],
            "outcome_counts": dict(sorted(outcome_counts.items())),
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
    serialized_round_trip: bool = False,
    serialized_mat_version: Literal["5", "7.3"] = "5",
    mne_smoke_test: bool = True,
) -> DatasetVerification:
    """Verify every ``dataSub*.mat`` file in a local CND dataset.

    ``neural_unit`` is an explicit testing assumption for legacy datasets. It
    is recorded in the report and is never inferred. When omitted, parsing and
    validation run but MNE and round-trip checks are skipped.

    ``serialized_round_trip`` additionally writes the converted recording to a
    temporary MATLAB file and reads it back. It is opt-in because serializing
    every subject in a multi-gigabyte public collection can require substantial
    time and temporary disk space. Both supported writer formats can be tested
    with ``serialized_mat_version="5"`` or ``"7.3"``.
    """
    if serialized_mat_version not in {"5", "7.3"}:
        raise ValueError("serialized_mat_version must be '5' or '7.3'")
    if serialized_round_trip and not round_trip:
        raise ValueError("serialized_round_trip requires round_trip=True")
    supplied_path = Path(path).expanduser()
    source = supplied_path.resolve()
    data_directory = source / "dataCND" if (source / "dataCND").is_dir() else source
    discovered_files = sorted(
        {
            *data_directory.glob("dataSub*.mat"),
            *data_directory.glob("pre_dataSub*.mat"),
            *data_directory.glob("dataParticipant_*.mat"),
        },
        key=_subject_sort_key,
    )
    if not discovered_files:
        raise FileNotFoundError(
            f"No CND subject files found in {data_directory}; expected "
            "dataSub*.mat, pre_dataSub*.mat, or dataParticipant_*.mat"
        )
    skipped_empty_files = tuple(
        file.name for file in discovered_files if file.stat().st_size == 0
    )
    files = [file for file in discovered_files if file.stat().st_size > 0]
    if not files:
        raise FileNotFoundError(
            f"No non-empty CND subject files found in {data_directory}"
        )
    subjects = tuple(
        _verify_subject(
            file,
            neural_unit=neural_unit,
            strict_spec=strict_spec,
            round_trip=round_trip,
            serialized_round_trip=serialized_round_trip,
            serialized_mat_version=serialized_mat_version,
            mne_smoke_test=mne_smoke_test,
        )
        for file in files
    )
    return DatasetVerification(
        schema_version=4,
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
        serialized_round_trip_requested=(
            serialized_round_trip and neural_unit is not None
        ),
        serialized_mat_version=(
            serialized_mat_version
            if serialized_round_trip and neural_unit is not None
            else None
        ),
        mne_smoke_test_requested=mne_smoke_test and neural_unit is not None,
        skipped_empty_files=skipped_empty_files,
        subjects=subjects,
    )


def _verify_subject(
    neural_file: Path,
    *,
    neural_unit: str | None,
    strict_spec: bool,
    round_trip: bool,
    serialized_round_trip: bool,
    serialized_mat_version: Literal["5", "7.3"],
    mne_smoke_test: bool,
) -> SubjectVerification:
    started = time.monotonic()
    subject = _subject_label(neural_file)
    stage = "read"
    empty: dict[str, Any] = {
        "subject": subject,
        "outcome": "source_read_failure",
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
        "external_mne_views_verified": None,
        "mne_psd_finite": None,
        "round_trip_verified": False,
        "round_trip_max_abs_error_source_units": None,
        "cnd_metadata_preserved": None,
        "serialized_round_trip_verified": None,
        "serialized_round_trip_max_abs_error_source_units": None,
        "conversion_warnings": (),
        "failure": None,
    }
    try:
        recording = read_cnd(neural_file)
        stage = "validate"
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
        if report.errors:
            empty["outcome"] = "validation_failure"
            return SubjectVerification(
                **empty, elapsed_seconds=round(time.monotonic() - started, 6)
            )
        if neural_unit is None:
            empty["outcome"] = (
                "empty_neural_data"
                if empty["n_neural_samples"] == 0
                else "structural_pass"
            )
            return SubjectVerification(
                **empty, elapsed_seconds=round(time.monotonic() - started, 6)
            )

        stage = "convert"
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            converted = to_mne(recording, neural_unit=neural_unit)
        scale = _unit_scale(neural_unit, neural.data_type.strip().lower())
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
            nonempty = next((raw for raw in converted.raws if raw.n_times), None)
            psd_finite = _mne_psd_is_finite(nonempty) if nonempty is not None else False

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

        external_views_verified = None
        if neural.external_trials is not None:
            # Identity scaling and ``misc`` channel types exercise the adapter
            # without making an unsupported claim about the external signals'
            # physical units or physiological meaning.
            external_views_verified = True
            external_raws = converted.external_raws(unit="V", channel_types="misc")
            external_views_verified &= len(external_raws) == len(neural.external_trials)
            for source_trial, raw in zip(
                neural.external_trials, external_raws, strict=True
            ):
                expected = np.asarray(source_trial)
                external_views_verified &= raw.get_data().shape == expected.T.shape
                if raw.get_data().shape == expected.T.shape:
                    external_views_verified &= np.array_equal(
                        raw.get_data(), expected.T
                    )

        round_trip_verified = False
        round_trip_error = None
        metadata_preserved = None
        serialized_verified = None
        serialized_error = None
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
                and converted_back.neural.channel_locations_raw
                is neural.channel_locations_raw
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
            if serialized_round_trip:
                serialized_verified, serialized_error = _serialized_round_trip(
                    converted_back,
                    mat_version=serialized_mat_version,
                )

        empty.update(
            {
                "mne_created": True,
                "mne_shape_verified": shape_verified,
                "mne_max_abs_error_source_units": mne_error,
                "stimulus_mne_views_verified": stimulus_views_verified,
                "external_mne_views_verified": external_views_verified,
                "mne_psd_finite": psd_finite,
                "round_trip_verified": round_trip_verified,
                "round_trip_max_abs_error_source_units": round_trip_error,
                "cnd_metadata_preserved": metadata_preserved,
                "serialized_round_trip_verified": serialized_verified,
                "serialized_round_trip_max_abs_error_source_units": (serialized_error),
                "conversion_warnings": tuple(str(item.message) for item in caught),
            }
        )
        if empty["n_neural_samples"] == 0:
            empty["outcome"] = "empty_neural_data"
        elif (
            shape_verified
            and stimulus_views_verified is not False
            and external_views_verified is not False
            and (not round_trip or round_trip_verified)
            and (not serialized_round_trip or serialized_verified is True)
            and (not mne_smoke_test or psd_finite is True)
        ):
            empty["outcome"] = "complete_pass"
        else:
            empty["outcome"] = "verification_failure"
    except Exception as error:  # report each subject without aborting the matrix
        empty["failure"] = f"{type(error).__name__}: {error}"
        if stage == "read" and isinstance(error, CNDValidationError):
            empty["outcome"] = "validation_failure"
        else:
            empty["outcome"] = {
                "read": "source_read_failure",
                "validate": "validation_failure",
                "convert": "conversion_failure",
            }[stage]
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


def _serialized_round_trip(
    recording: CNDRecording, *, mat_version: Literal["5", "7.3"]
) -> tuple[bool, float]:
    """Exercise the real MATLAB writer and reader in an isolated directory."""
    with tempfile.TemporaryDirectory(prefix="cnd-mne-verify-") as temporary:
        destination = Path(temporary) / "dataCND"
        write_cnd(recording, destination, mat_version=mat_version)
        reloaded = read_cnd(
            destination, subject=1 if recording.neural is not None else None
        )

    expected_neural = recording.neural
    actual_neural = reloaded.neural
    if expected_neural is None or actual_neural is None:
        return expected_neural is actual_neural, 0.0
    if len(expected_neural.trials) != len(actual_neural.trials):
        return False, float("inf")
    errors = [
        _max_abs_error(expected, actual)
        for expected, actual in zip(
            expected_neural.trials, actual_neural.trials, strict=True
        )
    ]
    neural_equal = all(
        np.asarray(expected).shape == np.asarray(actual).shape
        and np.allclose(expected, actual, rtol=1e-12, atol=1e-12)
        for expected, actual in zip(
            expected_neural.trials, actual_neural.trials, strict=True
        )
    )
    stimulus_equal = _stimulus_values_equal(recording, reloaded)
    external_equal = _optional_trial_values_equal(
        expected_neural.external_trials, actual_neural.external_trials
    )
    essentials_equal = (
        actual_neural.sfreq == expected_neural.sfreq
        and actual_neural.data_type == expected_neural.data_type
        and actual_neural.device_name == expected_neural.device_name
        and actual_neural.data_unit == expected_neural.data_unit
        and actual_neural.original_trial_positions
        == expected_neural.original_trial_positions
        and actual_neural.channel_names == expected_neural.channel_names
        and _metadata_equal(actual_neural.rereference, expected_neural.rereference)
        and _metadata_equal(
            actual_neural.padding_start_sample,
            expected_neural.padding_start_sample,
        )
        and actual_neural.cnd_version == expected_neural.cnd_version
    )
    return (
        neural_equal and stimulus_equal and external_equal and essentials_equal,
        max(errors, default=0.0),
    )


def _stimulus_values_equal(expected: CNDRecording, actual: CNDRecording) -> bool:
    expected_stimulus = expected.stimulus
    actual_stimulus = actual.stimulus
    if expected_stimulus is None or actual_stimulus is None:
        return expected_stimulus is actual_stimulus
    if (
        expected_stimulus.names != actual_stimulus.names
        or expected_stimulus.sfreq != actual_stimulus.sfreq
        or expected_stimulus.stimulus_indices != actual_stimulus.stimulus_indices
        or expected_stimulus.condition_indices != actual_stimulus.condition_indices
        or expected_stimulus.condition_names != actual_stimulus.condition_names
        or expected_stimulus.cnd_version != actual_stimulus.cnd_version
        or len(expected_stimulus.features) != len(actual_stimulus.features)
    ):
        return False
    return all(
        np.asarray(before).shape == np.asarray(after).shape
        and np.array_equal(before, after)
        for before_feature, after_feature in zip(
            expected_stimulus.features, actual_stimulus.features, strict=True
        )
        for before, after in zip(before_feature, after_feature, strict=True)
    )


def _optional_trial_values_equal(
    expected: tuple[np.ndarray, ...] | None,
    actual: tuple[np.ndarray, ...] | None,
) -> bool:
    if expected is None or actual is None:
        return expected is actual
    return len(expected) == len(actual) and all(
        np.asarray(before).shape == np.asarray(after).shape
        and np.array_equal(before, after)
        for before, after in zip(expected, actual, strict=True)
    )


def _metadata_equal(expected: Any, actual: Any) -> bool:
    if expected is None or actual is None:
        return expected is actual
    try:
        result = expected == actual
    except (TypeError, ValueError):
        return False
    return bool(np.all(result))


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
    label = _subject_label(path)
    return (int(label), label) if label.isdigit() else (2**31 - 1, label)


def _subject_label(path: Path) -> str:
    stem = path.stem
    if stem.startswith("dataSub"):
        return stem.removeprefix("dataSub")
    if stem.startswith("pre_dataSub"):
        return stem.removeprefix("pre_dataSub")
    if stem.startswith("dataParticipant_"):
        return stem.removeprefix("dataParticipant_")
    return stem


def _optional_max(values: Any) -> float | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _package_version() -> str:
    try:
        return version("cnd-mne-converter")
    except PackageNotFoundError:
        return "unknown"
