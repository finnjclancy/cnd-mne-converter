from __future__ import annotations

from dataclasses import replace

import mne
import numpy as np
import pytest

from cnd_mne import (
    CNDAmbiguousUnitError,
    CNDRecording,
    CNDUnsupportedError,
    CNDValidationError,
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


def test_template_round_trip_preserves_cnd_only_metadata(sample_recording) -> None:
    converted = to_mne(sample_recording)
    converted.raws[0]._data += 2e-6

    converted_back = converted.to_cnd()

    assert converted_back.stimulus is sample_recording.stimulus
    assert converted_back.neural.extra_fields == sample_recording.neural.extra_fields
    assert (
        converted_back.neural.external_fields == sample_recording.neural.external_fields
    )
    assert converted_back.neural.original_trial_positions == (2, 1)
    np.testing.assert_allclose(
        converted_back.neural.trials[0],
        sample_recording.neural.trials[0] + 2,
    )


def test_explicit_concatenation_marks_boundaries(sample_recording) -> None:
    converted = to_mne(sample_recording)

    combined = converted.concatenate()

    assert combined.n_times == 220
    np.testing.assert_allclose(
        combined.get_data(),
        np.concatenate([raw.get_data() for raw in converted.raws], axis=1),
    )
    assert converted.trial_slices == (slice(0, 100), slice(100, 220))
    descriptions = list(combined.annotations.description)
    assert descriptions.count("BAD boundary") == 1
    assert descriptions.count("EDGE boundary") == 1
    assert "CND_TRIAL/1" in descriptions
    assert "CND_TRIAL/2" in descriptions
    assert all(len(raw.annotations) == 0 for raw in converted.raws)


def test_mne_metadata_loss_is_reported(sample_recording) -> None:
    raw = to_mne(sample_recording).raws[0]
    raw.set_annotations(mne.Annotations([0.1], [0.0], ["event"]))

    with pytest.warns(RuntimeWarning, match="annotations"):
        from_mne(raw)
    with pytest.raises(CNDUnsupportedError, match="annotations"):
        from_mne(raw, on_unsupported_metadata="raise")


def test_template_rejects_changed_trial_length(sample_recording) -> None:
    converted = to_mne(sample_recording)
    converted.raws[0].crop(tmax=0.5)

    with pytest.raises(CNDValidationError, match="length does not match"):
        converted.to_cnd()


def test_stimulus_features_have_independent_mne_views(sample_recording) -> None:
    converted = to_mne(sample_recording)

    envelope = converted.stimulus_raws("Envelope")
    onsets = converted.stimulus_raws(1)

    assert envelope[0].info["sfreq"] == 10.0
    assert envelope[0].ch_names == ["Envelope"]
    assert envelope[0].get_channel_types() == ["misc"]
    np.testing.assert_array_equal(
        envelope[0].get_data()[0], sample_recording.stimulus.features[0][0]
    )
    np.testing.assert_array_equal(
        onsets[1].get_data()[0], sample_recording.stimulus.features[1][1]
    )


def test_multidimensional_stimulus_feature_becomes_multiple_channels(
    sample_recording,
) -> None:
    spectrogram = np.arange(30, dtype=float).reshape(10, 3)
    stimulus = replace(
        sample_recording.stimulus,
        names=("Spectrogram",),
        features=((spectrogram, np.zeros((12, 3))),),
    )
    converted = to_mne(CNDRecording(sample_recording.neural, stimulus))

    raw = converted.stimulus_raws("Spectrogram")[0]

    assert raw.ch_names == ["Spectrogram[01]", "Spectrogram[02]", "Spectrogram[03]"]
    np.testing.assert_array_equal(raw.get_data(), spectrogram.T)
