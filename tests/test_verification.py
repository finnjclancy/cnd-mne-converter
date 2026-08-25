from __future__ import annotations

import json

import mne
import numpy as np
import pytest
from scipy.io import savemat

from cnd_mne import CNDNeural, CNDRecording, verify_dataset, write_cnd
from cnd_mne.cli import main
from cnd_mne.verification import _mne_psd_is_finite


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
    assert subject.mne_psd_finite
    assert subject.round_trip_verified
    assert subject.mne_max_abs_error_source_units < 1e-12
    assert subject.round_trip_max_abs_error_source_units < 1e-12
    assert report.to_dict()["summary"]["n_trials"] == 2


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
            "--output",
            str(output),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    saved = json.loads(output.read_text())

    assert result == 0
    assert printed == saved
    assert saved["summary"]["passed"]


def test_verify_without_unit_performs_structural_checks_only(
    sample_recording, tmp_path
) -> None:
    write_cnd(sample_recording, tmp_path)

    report = verify_dataset(tmp_path)
    subject = report.subjects[0]

    assert report.passed
    assert subject.outcome == "structural_pass"
    assert not report.round_trip_requested
    assert not report.mne_smoke_test_requested
    assert not subject.mne_created


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
    assert report.to_dict()["summary"]["n_failed_subjects"] == 1


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
