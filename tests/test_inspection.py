from __future__ import annotations

import json

from cnd_mne import inspect_cnd, write_cnd
from cnd_mne.cli import main


def test_inspection_is_json_serializable(sample_recording) -> None:
    summary = inspect_cnd(sample_recording)

    assert summary["n_trials"] == 2
    assert summary["neural"]["n_channels"] == 2
    assert summary["stimulus"]["feature_names"] == ["Envelope", "Word Onsets"]
    assert summary["validation"]["is_valid"]
    json.dumps(summary)


def test_inspect_cli(sample_recording, tmp_path, capsys) -> None:
    write_cnd(sample_recording, tmp_path, subject=1)

    result = main(
        [
            "inspect",
            str(tmp_path),
            "--subject",
            "1",
            "--neural-variable",
            "eeg",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert result == 0
    assert output["neural"]["n_trials"] == 2
