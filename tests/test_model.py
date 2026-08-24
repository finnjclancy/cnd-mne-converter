from __future__ import annotations

from dataclasses import replace

import numpy as np

from cnd_mne import CNDRecording, CNDStimulus


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


def test_empty_and_stimulus_only_trial_metadata() -> None:
    empty = CNDRecording()
    stimulus = CNDStimulus(
        names=(),
        features=(),
        sfreq=10.0,
        stimulus_indices=(7,),
        condition_indices=(2,),
        condition_names=("only one",),
    )

    assert empty.n_trials == 0
    assert empty.trial_metadata == ()
    metadata = CNDRecording(stimulus=stimulus).trial_metadata[0]
    assert metadata.stimulus_index == 7
    assert metadata.condition_name is None
    assert metadata.stimulus_samples is None


def test_feature_lookup_and_condition_name_edge_cases(sample_recording) -> None:
    assert sample_recording.stimulus.feature("Envelope")[0].shape == (10,)
    try:
        sample_recording.stimulus.feature("missing")
    except KeyError as error:
        assert error.args == ("missing",)
    else:
        raise AssertionError("missing feature should raise KeyError")

    stimulus = replace(
        sample_recording.stimulus,
        condition_indices=(1.0, np.nan),
    )
    names = [
        trial.condition_name for trial in CNDRecording(stimulus=stimulus).trial_metadata
    ]
    assert names == ["A", None]


def test_incomplete_channel_labels_have_no_resolved_names(sample_recording) -> None:
    neural = replace(
        sample_recording.neural,
        channel_locations=({"labels": "Cz"}, {"X": 0.0}),
    )

    assert neural.channel_names is None
