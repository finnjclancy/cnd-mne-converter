from __future__ import annotations

from dataclasses import replace

from cnd_mne import CNDRecording


def test_trial_metadata_resolves_indices_conditions_and_durations(
    sample_recording,
) -> None:
    first, second = sample_recording.trial_metadata

    assert first.index == 0
    assert first.cnd_index == 1
    assert first.stimulus_index == 1
    assert first.condition_index == 1
    assert first.condition_name == "A"
    assert first.original_position == 2
    assert first.neural_duration_seconds == 1.0
    assert first.stimulus_duration_seconds == 1.0
    assert second.condition_name == "B"


def test_string_condition_is_its_own_readable_name(sample_recording) -> None:
    stimulus = replace(
        sample_recording.stimulus,
        condition_indices=("dry", "hrtf"),
        condition_names=None,
    )

    metadata = CNDRecording(sample_recording.neural, stimulus).trial_metadata

    assert [trial.condition_name for trial in metadata] == ["dry", "hrtf"]
