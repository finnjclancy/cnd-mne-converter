from __future__ import annotations

import json

from cnd_mne import verify_dataset, write_cnd
from cnd_mne.cli import main


def test_verify_dataset_exercises_mne_and_round_trip(
    sample_recording, tmp_path
) -> None:
    write_cnd(sample_recording, tmp_path, subject=1)

    report = verify_dataset(tmp_path, neural_unit="uV")
    subject = report.subjects[0]

    assert report.passed
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
