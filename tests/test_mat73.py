from __future__ import annotations

import h5py
import numpy as np

from cnd_mne import read_cnd, write_cnd


def _reference_dataset(group, name, targets, *, matlab_class="cell"):
    dataset = group.create_dataset(name, shape=(len(targets), 1), dtype=h5py.ref_dtype)
    dataset.attrs["MATLAB_class"] = np.bytes_(matlab_class)
    for index, target in enumerate(targets):
        dataset[index, 0] = target.ref
    return dataset


def _numeric_reference(refs, name, value):
    array = np.asarray(value)
    stored = array.T if array.ndim >= 2 else array[np.newaxis, :]
    dataset = refs.create_dataset(name, data=stored)
    dataset.attrs["MATLAB_class"] = np.bytes_("double")
    return dataset


def _char(group, name, text):
    codes = np.asarray([ord(character) for character in text], dtype=np.uint16)
    dataset = group.create_dataset(
        name,
        data=codes[:, None],
    )
    dataset.attrs["MATLAB_class"] = np.bytes_("char")
    return dataset


def test_matlab_v73_cnd_is_decoded(tmp_path) -> None:
    neural_path = tmp_path / "dataSub1.mat"
    stimulus_path = tmp_path / "dataStim1.mat"
    with h5py.File(neural_path, "w", userblock_size=512) as handle:
        refs = handle.create_group("#refs#")
        trial_1 = _numeric_reference(refs, "a", np.arange(12.0).reshape(6, 2))
        trial_2 = _numeric_reference(refs, "b", np.arange(16.0).reshape(8, 2))
        eeg = handle.create_group("eeg")
        eeg.attrs["MATLAB_class"] = np.bytes_("struct")
        _reference_dataset(eeg, "data", [trial_1, trial_2])
        eeg.create_dataset("fs", data=np.array([[100.0]])).attrs["MATLAB_class"] = (
            np.bytes_("double")
        )
        _char(eeg, "dataType", "EEG")
        _char(eeg, "dataUnit", "uV")

    with h5py.File(stimulus_path, "w", userblock_size=512) as handle:
        refs = handle.create_group("#refs#")
        feature_1 = _numeric_reference(refs, "a", np.arange(6.0))
        feature_2 = _numeric_reference(refs, "b", np.arange(8.0))
        stim = handle.create_group("stim")
        stim.attrs["MATLAB_class"] = np.bytes_("struct")
        _reference_dataset(stim, "data", [feature_1, feature_2])
        stim.create_dataset("fs", data=np.array([[100.0]])).attrs["MATLAB_class"] = (
            np.bytes_("double")
        )
        _char(stim, "names", "Envelope")
        stim.create_dataset("stimIdxs", data=np.array([[1], [2]], dtype=np.int32))

    recording = read_cnd(neural_path)

    assert recording.neural.trials[0].shape == (6, 2)
    assert recording.neural.trials[1].shape == (8, 2)
    assert recording.neural.data_unit == "uV"
    assert recording.stimulus.names == ("Envelope",)
    assert [trial.shape for trial in recording.stimulus.features[0]] == [(6,), (8,)]
    assert recording.stimulus.stimulus_indices == (1, 2)

    converted_directory = tmp_path / "converted"
    paths = write_cnd(recording, converted_directory)
    converted = read_cnd(paths.neural, stimulus_path=paths.stimulus)
    np.testing.assert_array_equal(
        converted.neural.trials[1], recording.neural.trials[1]
    )
    np.testing.assert_array_equal(
        converted.stimulus.features[0][1], recording.stimulus.features[0][1]
    )
