from __future__ import annotations

import json
import tempfile
from dataclasses import replace
from pathlib import Path

import mne
import numpy as np
import pytest
from scipy.io import savemat

from cnd_mne import CNDNeural, CNDRecording, verify_dataset, write_cnd
from cnd_mne.cli import main
from cnd_mne.verification import (
    _metadata_equal,
    _mne_psd_is_finite,
    _optional_trial_values_equal,
    _safe_failure_message,
    _serialized_round_trip,
    _stimulus_values_equal,
)


def test_verify_dataset_exercises_mne_and_round_trip(
    sample_recording, tmp_path
) -> None:
    write_cnd(sample_recording, tmp_path, subject=1)

    report = verify_dataset(tmp_path, neural_unit="uV")
    subject = report.subjects[0]

    assert report.passed
    assert subject.outcome == "complete_pass"
    assert subject.mne_created
    assert subject.mne_shape_verified
    assert subject.stimulus_mne_views_verified
    assert subject.external_mne_views_verified
    assert subject.mne_psd_finite
    assert subject.round_trip_verified
    assert subject.mne_max_abs_error_source_units < 1e-12
    assert subject.round_trip_max_abs_error_source_units < 1e-12
    assert report.to_dict()["summary"]["n_trials"] == 2


@pytest.mark.parametrize("mat_version", ["5", "7.3"])
def test_verify_dataset_can_exercise_serialized_round_trip(
    sample_recording, tmp_path, mat_version
) -> None:
    write_cnd(sample_recording, tmp_path, subject=1)

    report = verify_dataset(
        tmp_path,
        neural_unit="uV",
        serialized_round_trip=True,
        serialized_mat_version=mat_version,
    )
    subject = report.subjects[0]

    assert report.passed
    assert report.schema_version == 4
    assert report.serialized_round_trip_requested
    assert report.serialized_mat_version == mat_version
    assert subject.serialized_round_trip_verified
    assert subject.serialized_round_trip_max_abs_error_source_units < 1e-12


def test_verify_cli_writes_json_report(sample_recording, tmp_path, capsys) -> None:
    dataset = tmp_path / "dataset"
    output = tmp_path / "report.json"
    write_cnd(sample_recording, dataset, subject=1)

    result = main(
        [
            "verify-dataset",
            str(dataset),
            "--neural-unit",
            "uV",
            "--serialized-round-trip",
            "--mat-version",
            "7.3",
            "--output",
            str(output),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    saved = json.loads(output.read_text())

    assert result == 0
    assert printed == saved
    assert saved["summary"]["passed"]
    assert saved["serialized_round_trip_requested"]
    assert saved["serialized_mat_version"] == "7.3"
    assert saved["dataset_path"] == "dataset"
    assert str(tmp_path) not in json.dumps(saved)


def test_verify_without_unit_performs_structural_checks_only(
    sample_recording, tmp_path
) -> None:
    write_cnd(sample_recording, tmp_path)

    report = verify_dataset(tmp_path)
    subject = report.subjects[0]

    assert report.passed
    assert subject.outcome == "structural_pass"
    assert not report.round_trip_requested
    assert not report.serialized_round_trip_requested
    assert not report.mne_smoke_test_requested
    assert not subject.mne_created


def test_serialized_verification_arguments_are_consistent(
    sample_recording, tmp_path
) -> None:
    write_cnd(sample_recording, tmp_path)

    with pytest.raises(ValueError, match="serialized_mat_version"):
        verify_dataset(tmp_path, serialized_mat_version="8")
    with pytest.raises(ValueError, match="requires round_trip"):
        verify_dataset(tmp_path, serialized_round_trip=True, round_trip=False)


def test_serialized_comparison_helpers_cover_optional_and_changed_data(
    sample_recording,
) -> None:
    stimulus_only = CNDRecording(stimulus=sample_recording.stimulus)
    assert _serialized_round_trip(stimulus_only, mat_version="5") == (True, 0.0)

    assert _stimulus_values_equal(stimulus_only, stimulus_only)
    assert not _stimulus_values_equal(stimulus_only, CNDRecording())
    changed_stimulus = replace(sample_recording.stimulus, names=("changed", "onset"))
    assert not _stimulus_values_equal(
        stimulus_only, CNDRecording(stimulus=changed_stimulus)
    )

    trials = (np.ones((2, 1)),)
    assert _optional_trial_values_equal(None, None)
    assert not _optional_trial_values_equal(None, trials)
    assert _optional_trial_values_equal(trials, trials)
    assert not _optional_trial_values_equal(trials, (np.zeros((2, 1)),))

    assert _metadata_equal(None, None)
    assert not _metadata_equal(None, 1)
    assert _metadata_equal(np.array([1, 2]), np.array([1, 2]))
    assert not _metadata_equal(np.array([1, 2]), np.array([1, 3]))


def test_verify_reports_missing_dataset_and_subject_failure(
    sample_recording, tmp_path
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError, match="No CND subject"):
        verify_dataset(empty)

    dataset = tmp_path / "dataset"
    paths = write_cnd(sample_recording, dataset)
    paths.neural.write_bytes(b"truncated")

    report = verify_dataset(dataset, neural_unit="V")

    assert not report.passed
    assert report.subjects[0].outcome == "source_read_failure"
    assert report.subjects[0].failure.startswith("CNDReadError:")
    assert str(tmp_path) not in report.subjects[0].failure
    assert "dataSub1.mat" in report.subjects[0].failure
    assert report.to_dict()["summary"]["n_failed_subjects"] == 1


def test_failure_message_hides_temporary_directory() -> None:
    temporary_file = Path(tempfile.gettempdir()) / "private" / "dataSub1.mat"
    failure = _safe_failure_message(
        RuntimeError(f"failed beside {temporary_file.parent}"), temporary_file
    )

    assert failure.startswith("RuntimeError: failed beside <temporary>")
    assert failure.endswith("private")


def test_verify_distinguishes_invalid_cnd_from_unreadable_source(tmp_path) -> None:
    savemat(
        tmp_path / "dataSub1.mat",
        {"eeg": {"data": np.ones((4, 2)), "fs": -1.0, "dataType": "EEG"}},
    )

    report = verify_dataset(tmp_path, neural_unit="V")

    assert not report.passed
    assert report.subjects[0].outcome == "validation_failure"


def test_verify_reports_and_skips_empty_subject_placeholder(
    sample_recording, tmp_path
) -> None:
    write_cnd(sample_recording, tmp_path, subject=1)
    (tmp_path / "dataSub2.mat").touch()

    report = verify_dataset(tmp_path, neural_unit="V")
    summary = report.to_dict()["summary"]

    assert report.passed
    assert report.skipped_empty_files == ("dataSub2.mat",)
    assert summary["n_discovered_subject_files"] == 2
    assert summary["n_skipped_empty_files"] == 1
    assert summary["n_subjects"] == 1


def test_verifier_discovers_named_participant_files(sample_recording, tmp_path) -> None:
    paths = write_cnd(sample_recording, tmp_path)
    paths.neural.rename(tmp_path / "dataParticipant_P001.mat")
    paths.stimulus.rename(tmp_path / "dataStim_P001.mat")

    report = verify_dataset(tmp_path, neural_unit="V")

    assert report.passed
    assert report.subjects[0].subject == "P001"


def test_verifier_discovers_prefixed_subject_files(sample_recording, tmp_path) -> None:
    paths = write_cnd(sample_recording, tmp_path, subject=7)
    paths.neural.rename(tmp_path / "pre_dataSub7.mat")

    report = verify_dataset(tmp_path, neural_unit="V")

    assert report.passed
    assert report.subjects[0].subject == "7"


def test_psd_smoke_test_rejects_single_sample() -> None:
    raw = mne.io.RawArray(
        np.zeros((1, 1)), mne.create_info(["Cz"], 100.0, "eeg"), verbose="ERROR"
    )

    assert not _mne_psd_is_finite(raw)


def test_verifier_preserves_partial_trials_and_rejects_all_empty(tmp_path) -> None:
    partial = CNDRecording(
        neural=CNDNeural(
            trials=(np.empty((0, 2)), np.ones((4, 2))),
            sfreq=10.0,
            data_unit="V",
        )
    )
    write_cnd(partial, tmp_path / "partial")
    partial_report = verify_dataset(tmp_path / "partial", neural_unit="V")

    assert partial_report.passed
    assert partial_report.subjects[0].mne_psd_finite
    assert partial_report.subjects[0].warning_counts["empty_neural_trial"] == 1

    empty = CNDRecording(
        neural=CNDNeural(
            trials=(np.empty((0, 2)),),
            sfreq=10.0,
            data_unit="V",
        )
    )
    write_cnd(empty, tmp_path / "empty")
    empty_report = verify_dataset(tmp_path / "empty", neural_unit="V")

    assert empty_report.passed
    assert empty_report.subjects[0].outcome == "empty_neural_data"
    summary = empty_report.to_dict()["summary"]
    assert summary["n_failed_subjects"] == 0
    assert summary["n_empty_neural_files"] == 1
    assert summary["outcome_counts"] == {"empty_neural_data": 1}
