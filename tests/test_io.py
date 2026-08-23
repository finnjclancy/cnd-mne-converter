from __future__ import annotations

import numpy as np
import pytest

from cnd_mne import CNDReadError, CNDRecording, read_cnd, write_cnd


def test_cnd_matlab_round_trip(sample_recording, tmp_path) -> None:
    paths = write_cnd(sample_recording, tmp_path, subject="01")

    assert paths.neural == tmp_path / "dataSub01.mat"
    assert paths.stimulus == tmp_path / "dataStim.mat"
    loaded = read_cnd(tmp_path, subject="01")

    assert loaded.neural is not None
    assert loaded.stimulus is not None
    assert loaded.neural.data_type == "EEG"
    assert loaded.neural.device_name == "Synthetic"
    assert loaded.neural.data_unit == "uV"
    assert loaded.neural.original_trial_positions == (2, 1)
    assert loaded.neural.channel_names == ("Cz", "Pz")
    assert loaded.neural.extra_fields["customField"] == "preserve me"
    assert loaded.stimulus.names == ("Envelope", "Word Onsets")
    assert loaded.stimulus.condition_names == ("A", "B")
    assert loaded.stimulus.extra_fields["customStimField"] == 42
    for expected, actual in zip(
        sample_recording.neural.trials, loaded.neural.trials, strict=True
    ):
        np.testing.assert_array_equal(actual, expected)
    for expected_feature, actual_feature in zip(
        sample_recording.stimulus.features, loaded.stimulus.features, strict=True
    ):
        for expected, actual in zip(expected_feature, actual_feature, strict=True):
            np.testing.assert_array_equal(actual, expected)


def test_writer_protects_existing_files(sample_recording, tmp_path) -> None:
    write_cnd(sample_recording, tmp_path)
    with pytest.raises(FileExistsError):
        write_cnd(sample_recording, tmp_path)


def test_directory_requires_subject_when_multiple(sample_recording, tmp_path) -> None:
    write_cnd(sample_recording, tmp_path, subject=1)
    write_cnd(
        type(sample_recording)(neural=sample_recording.neural),
        tmp_path,
        subject=2,
    )
    with pytest.raises(CNDReadError, match="pass subject"):
        read_cnd(tmp_path)


def test_legacy_subject_specific_stimulus_layout(sample_recording, tmp_path) -> None:
    data_directory = tmp_path / "dataCND"
    stimulus_directory = tmp_path / "stimCND"
    legacy_stimulus = type(sample_recording.stimulus)(
        names=sample_recording.stimulus.names,
        features=sample_recording.stimulus.features,
        sfreq=sample_recording.stimulus.sfreq,
        stimulus_indices=None,
        condition_indices=("dry", "hrtf"),
        condition_names=None,
    )
    write_cnd(CNDRecording(neural=sample_recording.neural), data_directory)
    paths = write_cnd(CNDRecording(stimulus=legacy_stimulus), stimulus_directory)
    paths.stimulus.rename(stimulus_directory / "dataStim1.mat")

    loaded = read_cnd(tmp_path, subject=1)

    assert loaded.stimulus is not None
    assert loaded.stimulus.stimulus_indices is None
    assert loaded.stimulus.resolved_stimulus_indices == (1, 2)
    assert loaded.stimulus.condition_indices == ("dry", "hrtf")
