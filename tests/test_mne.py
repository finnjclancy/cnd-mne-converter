from __future__ import annotations

from dataclasses import replace

import mne
import numpy as np
import pytest

from cnd_mne import (
    CNDAmbiguousUnitError,
    CNDNeural,
    CNDRecording,
    CNDUnsupportedError,
    CNDValidationError,
    from_mne,
    read_cnd_mne,
    to_mne,
    write_cnd,
)
from cnd_mne.mne import MNECNDRecording


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
    sample_recording.additional_variables["pupilDilation"] = {
        "data": np.arange(2.0),
        "fs": 100.0,
        "dataType": "PupilDilation",
    }
    converted = to_mne(sample_recording)
    converted.raws[0]._data += 2e-6

    converted_back = converted.to_cnd()

    assert converted_back.stimulus is sample_recording.stimulus
    assert converted_back.neural.extra_fields == sample_recording.neural.extra_fields
    assert (
        converted_back.neural.external_fields == sample_recording.neural.external_fields
    )
    assert converted_back.neural.original_trial_positions == (2, 1)
    assert converted_back.additional_variables == sample_recording.additional_variables
    np.testing.assert_allclose(
        converted_back.neural.trials[0],
        sample_recording.neural.trials[0] + 2,
    )


def test_template_round_trip_preserves_absent_original_positions(
    sample_recording,
) -> None:
    recording = CNDRecording(
        replace(sample_recording.neural, original_trial_positions=None),
        sample_recording.stimulus,
    )

    converted_back = to_mne(recording).to_cnd()

    assert converted_back.neural.original_trial_positions is None


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


def test_sparse_stimulus_feature_becomes_opt_in_annotations(sample_recording) -> None:
    converted = to_mne(sample_recording)

    annotations = converted.stimulus_annotations("Word Onsets")
    valued = converted.stimulus_annotations(1, include_values=True)

    assert len(annotations) == 2
    assert annotations[0].onset.tolist() == [0.2]
    assert annotations[1].onset.tolist() == [0.3]
    assert annotations[0].description.tolist() == ["CND_STIM/Word Onsets"]
    assert valued[0].description.tolist() == ["CND_STIM/Word Onsets/1"]


def test_stimulus_annotation_policy_is_explicit(sample_recording) -> None:
    converted = to_mne(sample_recording)
    spectrogram = np.ones((10, 2))
    stimulus = replace(
        sample_recording.stimulus,
        names=("Spectrogram",),
        features=((spectrogram, spectrogram),),
    )

    with pytest.raises(ValueError, match="threshold"):
        converted.stimulus_annotations(1, threshold=-1)
    with pytest.raises(CNDValidationError, match="one-dimensional"):
        to_mne(CNDRecording(sample_recording.neural, stimulus)).stimulus_annotations(0)


def test_external_channels_have_explicit_separate_mne_views(sample_recording) -> None:
    converted = to_mne(sample_recording)

    external = converted.external_raws(
        unit="uV",
        channel_names=("M1", "M2"),
        channel_types=("eeg", "eeg"),
    )

    assert [raw.n_times for raw in external] == [100, 120]
    assert external[0].ch_names == ["M1", "M2"]
    assert external[0].get_channel_types() == ["eeg", "eeg"]
    np.testing.assert_allclose(external[1].get_data(), 2e-6)


def test_external_channel_mapping_rejects_ambiguity(sample_recording) -> None:
    converted = to_mne(sample_recording)
    without_external = to_mne(
        CNDRecording(replace(sample_recording.neural, external_trials=None))
    )

    with pytest.raises(CNDValidationError, match="no external"):
        without_external.external_raws(unit="V")
    with pytest.raises(CNDValidationError, match="match"):
        converted.external_raws(unit="V", channel_names=("only-one",))
    with pytest.raises(CNDValidationError, match="unique"):
        converted.external_raws(unit="V", channel_names=("M", "M"))


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


def test_empty_and_stimulus_only_recordings_are_rejected(sample_recording) -> None:
    empty_mne = MNECNDRecording((), CNDRecording(), "uV")
    with pytest.raises(CNDValidationError, match="empty"):
        empty_mne.concatenate()
    with pytest.raises(CNDValidationError, match="no stimulus"):
        empty_mne.stimulus_raws(0)

    with pytest.raises(CNDValidationError, match="no neural"):
        to_mne(CNDRecording(stimulus=sample_recording.stimulus))


def test_stimulus_feature_lookup_errors_are_explicit(sample_recording) -> None:
    converted = to_mne(sample_recording)

    with pytest.raises(KeyError, match="missing"):
        converted.stimulus_raws("missing")
    with pytest.raises(IndexError):
        converted.stimulus_raws(99)


def test_non_eeg_and_unknown_units_are_rejected(sample_recording) -> None:
    meg = replace(sample_recording.neural, data_type="MEG")
    with pytest.raises(CNDUnsupportedError, match="EEG and fNIRS"):
        to_mne(CNDRecording(neural=meg))
    with pytest.raises(ValueError, match="Unsupported EEG unit"):
        to_mne(sample_recording, neural_unit="arbitrary")


def test_fnirs_conversion_and_template_round_trip() -> None:
    trial = np.arange(60.0).reshape(10, 6)
    neural = CNDNeural(
        trials=(trial,),
        sfreq=25.0,
        data_type="fNIRS",
        original_trial_positions=(1,),
        data_unit="uM",
        signal_types=("HbO", "HbR", "HbT"),
        channels_per_signal_type=(2, 2, 2),
        variable_name="fnirs",
    )

    with pytest.warns(RuntimeWarning, match="generated stable names"):
        converted = to_mne(CNDRecording(neural=neural))
    raw = converted.raws[0]
    assert raw.get_channel_types() == ["hbo", "hbo", "hbr", "hbr", "misc", "misc"]
    assert raw.ch_names == ["HbO01", "HbO02", "HbR01", "HbR02", "HbT01", "HbT02"]
    np.testing.assert_allclose(raw.get_data(), trial.T * 1e-6)

    round_trip = converted.to_cnd()
    assert round_trip.neural.data_unit == "uM"
    assert round_trip.neural.signal_types == ("HbO", "HbR", "HbT")
    np.testing.assert_allclose(round_trip.neural.trials[0], trial)


@pytest.mark.parametrize(
    ("montage", "scale", "message"),
    [
        ("unknown", None, "Unknown montage"),
        ("eeglab", None, "positive coordinate"),
        ("eeglab", 0.0, "positive coordinate"),
    ],
)
def test_montage_policy_is_validated(sample_recording, montage, scale, message) -> None:
    with pytest.raises((ValueError, CNDValidationError), match=message):
        to_mne(
            sample_recording,
            montage=montage,
            coordinate_scale_to_meters=scale,
        )


def test_montage_requires_numeric_finite_xyz(sample_recording) -> None:
    missing = replace(
        sample_recording.neural,
        channel_locations=(
            {"labels": "Cz", "X": 0, "Y": 0},
            sample_recording.neural.channel_locations[1],
        ),
    )
    nonfinite = replace(
        sample_recording.neural,
        channel_locations=(
            {"labels": "Cz", "X": np.inf, "Y": 0, "Z": 0},
            sample_recording.neural.channel_locations[1],
        ),
    )

    with pytest.raises(CNDValidationError, match="lacks numeric"):
        to_mne(
            CNDRecording(neural=missing),
            montage="eeglab",
            coordinate_scale_to_meters=1.0,
        )
    with pytest.raises(CNDValidationError, match="non-finite"):
        to_mne(
            CNDRecording(neural=nonfinite),
            montage="eeglab",
            coordinate_scale_to_meters=1.0,
        )


def test_from_mne_requires_trials_eeg_and_valid_policy(sample_recording) -> None:
    raw = to_mne(sample_recording).raws[0]
    misc = mne.io.RawArray(
        raw.get_data(),
        mne.create_info(raw.ch_names, raw.info["sfreq"], "misc"),
        verbose="ERROR",
    )

    with pytest.raises(CNDValidationError, match="At least one"):
        from_mne([])
    with pytest.raises(ValueError, match="on_unsupported_metadata"):
        from_mne(raw, on_unsupported_metadata="invalid")
    with pytest.raises(CNDUnsupportedError, match="does not support channel types"):
        from_mne(misc)


def test_from_mne_requires_consistent_trials(sample_recording) -> None:
    first = to_mne(sample_recording).raws[0]
    different_rate = mne.io.RawArray(
        first.get_data(),
        mne.create_info(first.ch_names, 50.0, "eeg"),
        verbose="ERROR",
    )
    renamed = first.copy().rename_channels({"Cz": "Fz"})
    retyped = first.copy().set_channel_types({"Cz": "eog"})

    with pytest.raises(CNDValidationError, match="sampling rate"):
        from_mne([first, different_rate])
    with pytest.raises(CNDValidationError, match="channel names"):
        from_mne([first, renamed])
    with pytest.raises(CNDValidationError, match="channel types"):
        from_mne([first, retyped])


def test_template_compatibility_checks(sample_recording) -> None:
    converted = to_mne(sample_recording)
    stimulus_only = CNDRecording(stimulus=sample_recording.stimulus)

    with pytest.raises(CNDValidationError, match="template has no neural"):
        from_mne(converted.raws, template=stimulus_only)
    with pytest.raises(CNDValidationError, match="trial count"):
        from_mne(converted.raws[:1], template=sample_recording)
    renamed = list(converted.raws)
    renamed[0] = renamed[0].copy().rename_channels({"Cz": "Fz"})
    renamed[1] = renamed[1].copy().rename_channels({"Cz": "Fz"})
    with pytest.raises(CNDValidationError, match="CND template"):
        from_mne(renamed, template=sample_recording)
    with pytest.raises(CNDValidationError, match="original_trial_positions"):
        from_mne(converted.raws, original_trial_positions=[1])


def test_mne_montage_is_exported_to_cnd() -> None:
    info = mne.create_info(["Cz", "Pz"], 100.0, "eeg")
    raw = mne.io.RawArray(np.zeros((2, 20)), info, verbose="ERROR")
    raw.set_montage(
        mne.channels.make_dig_montage(
            ch_pos={"Cz": [0.0, 0.0, 0.1], "Pz": [0.0, -0.05, 0.08]},
            coord_frame="head",
        )
    )

    recording = from_mne(raw, output_unit="µV")

    assert recording.neural.data_unit == "uV"
    assert recording.neural.extra_fields == {
        "coordUnit": "m",
        "coordTransform": "MNE-head-to-EEGLAB-axis",
    }
    np.testing.assert_allclose(
        [recording.neural.channel_locations[1][axis] for axis in ("X", "Y", "Z")],
        [-0.05, 0.0, 0.08],
    )


def test_partial_mne_montage_falls_back_to_labels() -> None:
    info = mne.create_info(["Cz", "Pz"], 100.0, "eeg")
    raw = mne.io.RawArray(np.zeros((2, 20)), info, verbose="ERROR")
    raw.set_montage(
        mne.channels.make_dig_montage(
            ch_pos={"Cz": [0.0, 0.0, 0.1]}, coord_frame="head"
        ),
        on_missing="ignore",
    )

    recording = from_mne(raw)

    assert recording.neural.channel_locations == (
        {"labels": "Cz"},
        {"labels": "Pz"},
    )


def test_all_unsupported_mne_metadata_is_reported(sample_recording) -> None:
    source = to_mne(sample_recording).raws[0]
    info = source.info.copy()
    raw = mne.io.RawArray(source.get_data(), info, first_samp=10, verbose="ERROR")
    raw.info["bads"] = ["Cz"]
    raw.set_eeg_reference(projection=True, verbose="ERROR")

    with pytest.warns(RuntimeWarning) as caught:
        from_mne(raw)
    message = str(caught[0].message)
    assert "bad-channel list" in message
    assert "projection metadata" in message
    assert "non-zero first sample" in message

    from_mne(raw, on_unsupported_metadata="ignore")


def test_convenience_read_and_write_mne_api(sample_recording, tmp_path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    write_cnd(sample_recording, source)

    converted = read_cnd_mne(source, neural_unit="uV")
    paths = converted.write_cnd(
        destination,
        output_unit="uV",
        mat_version="7.3",
        on_unsupported_metadata="raise",
    )

    assert paths.neural.exists()
    reloaded = read_cnd_mne(destination, neural_unit="uV")
    np.testing.assert_allclose(
        reloaded.raws[0].get_data(), converted.raws[0].get_data()
    )


def test_mne_write_preserves_named_participant_files(
    sample_recording, tmp_path
) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    write_cnd(
        sample_recording,
        source,
        neural_filename="dataParticipant_P001.mat",
        stimulus_filename="dataStim_P001.mat",
    )

    converted = read_cnd_mne(source, subject="P001", neural_unit="uV")
    paths = converted.write_cnd(destination, output_unit="uV")

    assert paths.neural == destination / "dataParticipant_P001.mat"
    assert paths.stimulus == destination / "dataStim_P001.mat"
    assert read_cnd_mne(destination, subject="P001", neural_unit="uV").raws
