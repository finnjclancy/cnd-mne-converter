from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from cnd_mne import (
    CNDAmbiguousUnitError,
    CNDRecording,
    from_mne,
    to_mne,
)


def test_to_mne_transposes_and_converts_to_volts(sample_recording) -> None:
    converted = to_mne(sample_recording)

    assert len(converted.raws) == 2
    assert converted.raws[0].get_data().shape == (2, 100)
    np.testing.assert_allclose(
        converted.raws[0].get_data(),
        sample_recording.neural.trials[0].T * 1e-6,
    )
    assert converted.raws[0].info["sfreq"] == 100.0
    assert converted.raws[0].ch_names == ["Cz", "Pz"]
    assert converted.stimulus is sample_recording.stimulus


def test_to_mne_requires_unit(sample_recording) -> None:
    neural = replace(sample_recording.neural, data_unit=None)
    with pytest.raises(CNDAmbiguousUnitError):
        to_mne(CNDRecording(neural, sample_recording.stimulus))


def test_to_mne_missing_channels_is_explicit(sample_recording) -> None:
    neural = replace(sample_recording.neural, channel_locations=None)
    with pytest.warns(RuntimeWarning, match="generated"):
        converted = to_mne(CNDRecording(neural, sample_recording.stimulus))
    assert converted.raws[0].ch_names == ["EEG001", "EEG002"]
    assert converted.raws[0].get_montage() is None


def test_montage_requires_explicit_transform_and_scale(sample_recording) -> None:
    converted = to_mne(
        sample_recording,
        montage="eeglab",
        coordinate_scale_to_meters=0.095,
    )
    positions = converted.raws[0].get_montage().get_positions()["ch_pos"]

    np.testing.assert_allclose(positions["Cz"], [0.0, 0.0, 0.095])
    np.testing.assert_allclose(positions["Pz"], [0.0475, 0.0, 0.076])


def test_mne_to_cnd_preserves_values_and_metadata(sample_recording) -> None:
    mne_recording = to_mne(sample_recording)
    converted_back = from_mne(
        mne_recording.raws,
        stimulus=sample_recording.stimulus,
        output_unit="uV",
        device_name="Synthetic",
    )

    assert converted_back.neural is not None
    assert converted_back.neural.data_unit == "uV"
    assert converted_back.neural.channel_names == ("Cz", "Pz")
    for expected, actual in zip(
        sample_recording.neural.trials,
        converted_back.neural.trials,
        strict=True,
    ):
        np.testing.assert_allclose(actual, expected)
