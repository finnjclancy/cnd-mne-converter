from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from cnd_mne import (
    CNDNeural,
    CNDRecording,
    CNDStimulus,
    CNDValidationError,
    validate_cnd,
)


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


def test_sampling_rate_mismatch_has_tolerant_and_strict_modes(
    sample_recording,
) -> None:
    stimulus = replace(sample_recording.stimulus, sfreq=20.0)
    recording = CNDRecording(sample_recording.neural, stimulus)

    tolerant = validate_cnd(recording)
    strict = validate_cnd(recording, strict_spec=True)

    assert any(
        issue.code == "sampling_frequency_mismatch" for issue in tolerant.warnings
    )
    assert any(issue.code == "sampling_frequency_mismatch" for issue in strict.errors)


def test_invalid_sampling_rate_returns_report_instead_of_dividing_by_zero(
    sample_recording,
) -> None:
    neural = replace(sample_recording.neural, sfreq=0.0)

    report = validate_cnd(CNDRecording(neural, sample_recording.stimulus))

    assert any(issue.code == "invalid_sfreq" for issue in report.errors)


def test_negative_duration_tolerance_is_rejected(sample_recording) -> None:
    with pytest.raises(ValueError, match="non-negative"):
        validate_cnd(sample_recording, duration_tolerance_seconds=-1)


def test_empty_recording_raises_from_report() -> None:
    report = validate_cnd(CNDRecording())

    assert {issue.code for issue in report.errors} == {"empty_recording"}
    with pytest.raises(CNDValidationError, match="No neural or stimulus"):
        report.raise_for_errors()


def test_neural_metadata_and_shape_errors_are_reported(sample_recording) -> None:
    neural = replace(
        sample_recording.neural,
        trials=(np.zeros(5), np.zeros((0, 2))),
        original_trial_positions=(4,),
        channel_locations=({"labels": "Cz"},),
        external_trials=(np.zeros(5),),
        cnd_version="legacy",
    )

    report = validate_cnd(CNDRecording(neural=neural), strict_spec=True)
    codes = {issue.code for issue in report.errors}

    assert {
        "invalid_neural_shape",
        "empty_neural_trial",
        "trial_position_count",
        "channel_location_count",
        "non_numeric_cnd_version",
        "external_trial_count",
    } <= codes


def test_external_channel_shapes_and_lengths_are_reported(sample_recording) -> None:
    invalid_shape = replace(
        sample_recording.neural,
        external_trials=(np.zeros(100), np.zeros((120, 1))),
    )
    wrong_length = replace(
        sample_recording.neural,
        external_trials=(np.zeros((99, 1)), np.zeros((120, 1))),
    )

    assert any(
        issue.code == "invalid_external_shape"
        for issue in validate_cnd(CNDRecording(neural=invalid_shape)).errors
    )
    assert any(
        issue.code == "external_length_mismatch"
        for issue in validate_cnd(CNDRecording(neural=wrong_length)).warnings
    )


def test_duplicate_channel_names_and_invalid_positions(sample_recording) -> None:
    duplicate = replace(
        sample_recording.neural,
        channel_locations=({"labels": "Cz"}, {"labels": "Cz"}),
        original_trial_positions=(1, 1),
    )
    report = validate_cnd(CNDRecording(neural=duplicate), strict_spec=True)
    codes = {issue.code for issue in report.errors}

    assert "duplicate_channel_names" in codes
    assert "invalid_trial_positions" in codes


def test_stimulus_structure_errors_are_reported() -> None:
    stimulus = CNDStimulus(
        names=("Envelope", "Envelope", "Extra"),
        features=(
            (np.zeros(4), np.zeros(5)),
            (np.zeros(4),),
        ),
        sfreq=np.nan,
        stimulus_indices=(1,),
        condition_indices=(1,),
        cnd_version="legacy",
    )

    codes = {
        issue.code
        for issue in validate_cnd(
            CNDRecording(stimulus=stimulus), strict_spec=True
        ).errors
    }

    assert {
        "invalid_sfreq",
        "feature_name_count",
        "duplicate_feature_names",
        "stimulus_index_count",
        "stimulus_trial_count",
        "condition_index_count",
        "non_numeric_cnd_version",
    } <= codes


@pytest.mark.parametrize(
    ("trial", "expected_code"),
    [
        (np.zeros((1, 1, 1)), "invalid_stimulus_shape"),
        (np.zeros(0), "empty_stimulus_trial"),
    ],
)
def test_invalid_stimulus_trial_arrays(trial, expected_code) -> None:
    stimulus = CNDStimulus(names=("x",), features=((trial,),), sfreq=1.0)

    report = validate_cnd(CNDRecording(stimulus=stimulus))

    issues = (
        report.warnings if expected_code == "empty_stimulus_trial" else report.errors
    )
    assert any(issue.code == expected_code for issue in issues)
    if expected_code == "empty_stimulus_trial":
        strict = validate_cnd(CNDRecording(stimulus=stimulus), strict_spec=True)
        assert any(issue.code == expected_code for issue in strict.errors)


def test_paired_trial_and_feature_length_mismatches(sample_recording) -> None:
    unequal_features = replace(
        sample_recording.stimulus,
        features=((np.zeros(10), np.zeros(12)), (np.zeros(9), np.zeros(12))),
    )
    paired = replace(
        sample_recording.stimulus,
        features=((np.zeros(10),), (np.zeros(10),)),
        stimulus_indices=(1,),
        condition_indices=(1,),
    )

    unequal_recording = CNDRecording(stimulus=unequal_features)
    assert any(
        issue.code == "feature_length_mismatch"
        for issue in validate_cnd(unequal_recording).warnings
    )
    assert any(
        issue.code == "feature_length_mismatch"
        for issue in validate_cnd(unequal_recording, strict_spec=True).errors
    )
    recording = CNDRecording(sample_recording.neural, paired)
    assert any(
        issue.code == "paired_trial_count" for issue in validate_cnd(recording).warnings
    )
    assert any(
        issue.code == "paired_trial_count"
        for issue in validate_cnd(recording, strict_spec=True).errors
    )


def test_empty_neural_trials_are_reported() -> None:
    neural = CNDNeural(trials=(), sfreq=100.0)

    report = validate_cnd(CNDRecording(neural=neural))

    assert any(issue.code == "missing_trials" for issue in report.errors)

    partial = CNDRecording(neural=CNDNeural(trials=(np.empty((0, 2)),), sfreq=100.0))
    assert any(
        issue.code == "empty_neural_trial" for issue in validate_cnd(partial).warnings
    )
    assert any(
        issue.code == "empty_neural_trial"
        for issue in validate_cnd(partial, strict_spec=True).errors
    )


def test_paired_recording_without_stimulus_features_is_validated(
    sample_recording,
) -> None:
    stimulus = CNDStimulus(
        names=(),
        features=(),
        sfreq=sample_recording.neural.sfreq,
        stimulus_indices=(1, 2),
    )

    report = validate_cnd(CNDRecording(sample_recording.neural, stimulus))

    assert not report.errors
