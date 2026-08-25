from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
from scipy.io import savemat

import cnd_mne.io as cnd_io
from cnd_mne import (
    CNDReadError,
    CNDRecording,
    read_cnd,
    read_cnd_neural,
    read_cnd_stimulus,
    write_cnd,
)


def test_cnd_matlab_round_trip(sample_recording, tmp_path) -> None:
    paths = write_cnd(sample_recording, tmp_path, subject="01")

    assert paths.neural == tmp_path / "dataSub1.mat"
    assert paths.stimulus == tmp_path / "dataStim.mat"
    loaded = read_cnd(tmp_path, subject=1)

    assert loaded.neural is not None
    assert loaded.stimulus is not None
    assert loaded.neural.data_type == "EEG"
    assert loaded.neural.device_name == "Synthetic"
    assert loaded.neural.data_unit == "uV"
    assert loaded.neural.original_trial_positions == (2, 1)
    assert loaded.neural.channel_names == ("Cz", "Pz")
    assert loaded.neural.extra_fields["customField"] == "preserve me"
    assert loaded.neural.external_fields["channelType"] == "mastoids"
    assert loaded.neural.cnd_version == 1.0
    assert loaded.stimulus.names == ("Envelope", "Word Onsets")
    assert loaded.stimulus.condition_names == ("A", "B")
    assert loaded.stimulus.extra_fields["customStimField"] == 42
    assert loaded.stimulus.cnd_version == 1.0
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


def test_writer_preflights_all_outputs(sample_recording, tmp_path) -> None:
    write_cnd(CNDRecording(stimulus=sample_recording.stimulus), tmp_path)

    with pytest.raises(FileExistsError):
        write_cnd(sample_recording, tmp_path)

    assert not (tmp_path / "dataSub1.mat").exists()


@pytest.mark.parametrize("subject", [0, -1, "participant"])
def test_writer_requires_positive_numeric_subject(
    sample_recording, tmp_path, subject
) -> None:
    with pytest.raises(ValueError, match="positive numeric"):
        write_cnd(sample_recording, tmp_path, subject=subject)


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


def test_named_participant_stimulus_is_inferred(sample_recording, tmp_path) -> None:
    paths = write_cnd(sample_recording, tmp_path, subject=1)
    participant = tmp_path / "dataParticipant_P001.mat"
    stimulus = tmp_path / "dataStim_P001.mat"
    paths.neural.rename(participant)
    paths.stimulus.rename(stimulus)

    loaded = read_cnd(participant)
    loaded_from_directory = read_cnd(tmp_path, subject="P001")

    assert loaded.neural.n_trials == 2
    assert loaded.stimulus.n_trials == 2
    assert loaded_from_directory.neural.n_trials == 2


def test_prefixed_subject_and_parent_stimulus_are_inferred(
    sample_recording, tmp_path
) -> None:
    cohort = tmp_path / "cohort"
    paths = write_cnd(sample_recording, cohort, subject=7)
    prefixed = cohort / "pre_dataSub7.mat"
    paths.neural.rename(prefixed)
    paths.stimulus.rename(tmp_path / "dataStim7.mat")

    loaded = read_cnd(prefixed)
    loaded_from_directory = read_cnd(cohort, subject=7)

    assert loaded.neural.n_trials == 2
    assert loaded.stimulus.n_trials == 2
    assert loaded_from_directory.stimulus.n_trials == 2


def test_individual_neural_and_stimulus_files_can_be_read(
    sample_recording, tmp_path
) -> None:
    paths = write_cnd(sample_recording, tmp_path)

    neural_only = read_cnd(paths.neural, load_stimulus=False)
    stimulus_only = read_cnd(paths.stimulus)

    assert neural_only.neural is not None and neural_only.stimulus is None
    assert stimulus_only.neural is None and stimulus_only.stimulus is not None
    assert read_cnd_neural(paths.neural).n_trials == 2
    assert read_cnd_stimulus(paths.stimulus).n_features == 2

    inferred = read_cnd(paths.neural)
    explicit = read_cnd(paths.neural, stimulus_path=paths.stimulus)
    assert inferred.stimulus is not None
    assert explicit.stimulus is not None


def test_reader_reports_missing_and_unrecognized_files(tmp_path) -> None:
    missing = tmp_path / "missing.mat"
    with pytest.raises(FileNotFoundError):
        read_cnd(missing)

    unknown = tmp_path / "unknown.mat"
    savemat(unknown, {"answer": 42})
    with pytest.raises(CNDReadError, match="neither neural nor 'stim'"):
        read_cnd(unknown)
    with pytest.raises(CNDReadError, match="recognizable neural"):
        read_cnd_neural(unknown)
    with pytest.raises(CNDReadError, match="does not contain a 'stim'"):
        read_cnd_stimulus(unknown)


def test_reader_reports_corrupt_matlab_file(tmp_path) -> None:
    corrupt = tmp_path / "corrupt.mat"
    corrupt.write_bytes(b"not a MATLAB file")

    with pytest.raises(CNDReadError, match="Could not read MATLAB"):
        read_cnd(corrupt)


def test_directory_without_subjects_can_hold_stimulus_only(
    sample_recording, tmp_path
) -> None:
    write_cnd(CNDRecording(stimulus=sample_recording.stimulus), tmp_path)

    loaded = read_cnd(tmp_path)

    assert loaded.neural is None
    assert loaded.stimulus is not None


def test_explicit_missing_subject_is_reported(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="dataSub3.mat"):
        read_cnd(tmp_path, subject=3)


def test_writer_supports_overwrite_and_uncompressed_output(
    sample_recording, tmp_path
) -> None:
    first = write_cnd(sample_recording, tmp_path, compression=False)
    second = write_cnd(sample_recording, tmp_path, overwrite=True, compression=False)

    assert first == second
    assert read_cnd(tmp_path, subject=1).n_trials == 2
    assert read_cnd(tmp_path).n_trials == 2


def test_alternate_neural_variable_and_single_channel_are_supported(tmp_path) -> None:
    path = tmp_path / "custom.mat"
    savemat(
        path,
        {
            "brain": {
                "data": np.arange(8.0),
                "fs": 8.0,
                "dataType": "EEG",
                "unit": "uV",
                "chanlocs": {"labels": "Cz"},
            }
        },
    )

    neural = read_cnd_neural(path)

    assert neural.variable_name == "brain"
    assert neural.trials[0].shape == (8, 1)
    assert neural.channel_names == ("Cz",)


def test_parser_helpers_cover_supported_matlab_layouts() -> None:
    trials = cnd_io._as_trial_tuple(np.zeros((2, 3, 4)))
    assert [trial.shape for trial in trials] == [(3, 4), (3, 4)]
    assert len(cnd_io._as_trial_tuple([np.zeros(2), np.ones(3)])) == 2
    assert cnd_io._as_feature_tuple([], 0) == ()
    assert len(cnd_io._as_feature_tuple([np.zeros(2), np.ones(3)], 1)[0]) == 2
    assert len(cnd_io._as_feature_tuple([[np.zeros(2)], [np.ones(2)]], 2)) == 2
    object_features = np.empty(2, dtype=object)
    object_features[0] = [np.zeros(2)]
    object_features[1] = [np.ones(3)]
    assert len(cnd_io._as_feature_tuple(object_features, 2)) == 2
    assert cnd_io._as_feature_tuple(np.arange(3), 1)[0][0].shape == (3,)

    with pytest.raises(CNDReadError, match="Cannot interpret neural"):
        cnd_io._as_trial_tuple(np.zeros((1, 2, 3, 4)))
    with pytest.raises(CNDReadError, match="Cannot interpret stimulus"):
        cnd_io._as_feature_tuple(np.zeros((2, 2)), 3)


def test_channel_location_layouts_and_invalid_layout() -> None:
    columnar = cnd_io._parse_channel_locations(
        {"labels": np.array(["Cz", "Pz"]), "X": np.array([0.0, 1.0])}
    )
    listed = cnd_io._parse_channel_locations([{"labels": "Cz"}])

    assert columnar == (
        {"labels": "Cz", "X": 0.0},
        {"labels": "Pz", "X": 1.0},
    )
    assert listed == ({"labels": "Cz"},)
    assert cnd_io._parse_channel_locations(None) is None

    structured = np.array(
        [("Cz", 0.0), ("Pz", 1.0)],
        dtype=[("labels", "U2"), ("X", float)],
    )
    assert cnd_io._parse_channel_locations(structured) == (
        {"labels": "Cz", "X": 0.0},
        {"labels": "Pz", "X": 1.0},
    )
    object_array = np.empty(2, dtype=object)
    object_array[:] = [{"labels": "Cz"}, {"labels": "Pz"}]
    assert cnd_io._parse_channel_locations(object_array) == (
        {"labels": "Cz"},
        {"labels": "Pz"},
    )
    with pytest.raises(CNDReadError, match="chanlocs"):
        cnd_io._parse_channel_locations([1, 2])


def test_parser_helpers_report_malformed_structures(tmp_path) -> None:
    with pytest.raises(CNDReadError, match="not a MATLAB structure"):
        cnd_io._parse_neural(1, "eeg", tmp_path / "bad.mat")
    with pytest.raises(CNDReadError, match="missing 'fs'"):
        cnd_io._parse_neural({"data": np.zeros(4)}, "eeg", tmp_path / "bad.mat")
    with pytest.raises(CNDReadError, match="not a MATLAB structure"):
        cnd_io._parse_stimulus(1, tmp_path / "bad.mat")
    with pytest.raises(CNDReadError, match="missing"):
        cnd_io._parse_stimulus({"data": [], "names": []}, tmp_path / "bad.mat")


def test_matlab_v73_error_gets_actionable_message(monkeypatch, tmp_path) -> None:
    path = tmp_path / "v73.mat"
    path.touch()

    def unsupported(*args, **kwargs):
        raise NotImplementedError

    monkeypatch.setattr(cnd_io, "loadmat", unsupported)
    with pytest.raises(CNDReadError, match="v7.3/HDF5"):
        read_cnd(path)


def test_external_metadata_without_samples_and_optional_fields_round_trip(
    sample_recording, tmp_path
) -> None:
    neural = replace(
        sample_recording.neural,
        external_trials=None,
        external_description=None,
        external_fields={"channelType": "reference"},
        rereference="average",
        padding_start_sample=17,
    )

    paths = write_cnd(CNDRecording(neural=neural), tmp_path)
    loaded = read_cnd_neural(paths.neural)

    assert loaded.external_trials is None
    assert loaded.external_fields == {"channelType": "reference"}
    assert loaded.rereference == "average"
    assert loaded.padding_start_sample == 17


def test_multiple_external_channel_groups_are_combined_without_loss(tmp_path) -> None:
    groups = np.empty(2, dtype=object)
    groups[0] = {
        "description": "Mastoid left",
        "data": [np.arange(4.0), np.arange(5.0)],
        "kind": "reference",
    }
    groups[1] = {
        "description": "Mastoid right",
        "data": [np.arange(4.0) + 10, np.arange(5.0) + 10],
        "kind": "reference",
    }
    neural = cnd_io._parse_neural(
        {
            "data": [np.zeros((4, 2)), np.zeros((5, 2))],
            "fs": 10.0,
            "dataType": "EEG",
            "extChan": groups,
        },
        "eeg",
        tmp_path / "external.mat",
    )

    assert [trial.shape for trial in neural.external_trials] == [(4, 2), (5, 2)]
    assert neural.external_description == "Mastoid left; Mastoid right"
    assert neural.external_fields["groupDescriptions"] == (
        "Mastoid left",
        "Mastoid right",
    )
    assert neural.external_fields["groupFields"] == (
        {"kind": "reference"},
        {"kind": "reference"},
    )


def test_fnirs_signal_type_grid_is_normalized_and_written_losslessly(tmp_path) -> None:
    data = np.empty((3, 2), dtype=object)
    for signal_index in range(3):
        data[signal_index, 0] = np.full((4, 2), signal_index + 1.0)
        data[signal_index, 1] = np.full((5, 2), signal_index + 11.0)
    neural = cnd_io._parse_neural(
        {
            "data": data,
            "fs": 25.0,
            "dataType": "fNIRS",
            "datatype": np.array(["HbO", "HbR", "HbT"], dtype=object),
            "origTrialPosition": [1, 2],
        },
        "fnirs",
        tmp_path / "fnirs.mat",
    )

    assert neural.signal_types == ("HbO", "HbR", "HbT")
    assert neural.channels_per_signal_type == (2, 2, 2)
    assert [trial.shape for trial in neural.trials] == [(4, 6), (5, 6)]

    path = write_cnd(CNDRecording(neural=neural), tmp_path / "out").neural
    loaded = read_cnd_neural(path)
    assert loaded.signal_types == neural.signal_types
    assert loaded.channels_per_signal_type == neural.channels_per_signal_type
    for expected, actual in zip(neural.trials, loaded.trials, strict=True):
        np.testing.assert_array_equal(actual, expected)


def test_atomic_writer_cleans_temporary_file_on_failure(monkeypatch, tmp_path) -> None:
    destination = tmp_path / "output.mat"

    def fail(*args, **kwargs):
        raise RuntimeError("disk failure")

    monkeypatch.setattr(cnd_io, "savemat", fail)
    with pytest.raises(RuntimeError, match="disk failure"):
        cnd_io._atomic_savemat(destination, {"x": 1}, False, True)

    assert not destination.exists()
    assert not list(tmp_path.iterdir())


def test_small_path_and_scalar_helpers(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="dataStim.mat"):
        cnd_io._resolve_stimulus_file(tmp_path, None, required=True)
    assert cnd_io._subject_from_filename(tmp_path / "recording.mat") is None
    assert cnd_io._string_or_default(1, "EEG") == "EEG"
    assert cnd_io._matlab_value(None).shape == (0, 0)


def test_mcos_string_handles_are_decoded_from_workspace() -> None:
    dtype = [("_TypeSystem", object), ("_Class", object), ("_ObjectMetadata", object)]
    handles = np.empty(2, dtype=object)
    for index in range(2):
        handle = np.empty(1, dtype=dtype)
        handle[0] = ("MCOS", "string", np.array([0, 2, 1, 1, index + 1, 1]))
        handles[index] = handle
    workspace = np.frombuffer(
        b"prefix"
        + "Speech Envelope".encode("utf-16le")
        + b"\xff"
        + "Word Onsets".encode("utf-16le")
        + b"\xff",
        dtype=np.uint8,
    )

    decoded = cnd_io._decode_mcos_strings({"names": handles}, workspace)

    assert tuple(decoded["names"]) == ("Speech Envelope", "Word Onsets")


def test_empty_neural_cells_retain_inferred_channel_count(tmp_path) -> None:
    neural = cnd_io._parse_neural(
        {
            "data": [np.ones((3, 2)), np.array([])],
            "fs": 10.0,
            "dataType": "EEG",
        },
        "eeg",
        tmp_path / "partial.mat",
    )

    assert [trial.shape for trial in neural.trials] == [(3, 2), (0, 2)]
