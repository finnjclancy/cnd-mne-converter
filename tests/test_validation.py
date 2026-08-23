from __future__ import annotations

from dataclasses import replace

import numpy as np

from cnd_mne import CNDRecording, validate_cnd


def test_different_sample_rates_compare_in_seconds(sample_recording) -> None:
    report = validate_cnd(sample_recording)
    assert report.is_valid
    assert not any(issue.code == "duration_mismatch" for issue in report.issues)


def test_duration_mismatch_is_reported(sample_recording) -> None:
    stimulus = replace(
        sample_recording.stimulus,
        features=(
            (np.zeros(7), np.zeros(12)),
            (np.zeros(7), np.zeros(12)),
        ),
    )
    report = validate_cnd(CNDRecording(sample_recording.neural, stimulus))
    assert any(issue.code == "duration_mismatch" for issue in report.warnings)


def test_inconsistent_channel_count_is_an_error(sample_recording) -> None:
    neural = replace(
        sample_recording.neural,
        trials=(sample_recording.neural.trials[0], np.zeros((120, 3))),
    )
    report = validate_cnd(CNDRecording(neural, sample_recording.stimulus))
    assert any(issue.code == "channel_count_mismatch" for issue in report.errors)
