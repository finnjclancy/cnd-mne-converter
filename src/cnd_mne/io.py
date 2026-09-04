"""Read and write Continuous-event Neural Data MATLAB files."""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

import hdf5storage
import numpy as np
from scipy.io import loadmat, savemat
from scipy.io.matlab import MatReadError

from .exceptions import CNDReadError
from .mat73 import is_mat73, load_mat73
from .model import CNDNeural, CNDPaths, CNDRecording, CNDStimulus, ExternalLayout
from .validation import validate_cnd

_MATLAB_METADATA = {"__header__", "__version__", "__globals__"}
_NEURAL_RESERVED = {
    "data",
    "dataType",
    "deviceName",
    "origTrialPosition",
    "chanlocs",
    "extChan",
    "reRef",
    "paddingStartSample",
    "fs",
    "cndVersion",
    "dataUnit",
    "unit",
    "units",
    "datatype",
}
_STIMULUS_RESERVED = {
    "data",
    "names",
    "stimIdxs",
    "condIdxs",
    "condNames",
    "fs",
    "cndVersion",
}


def read_cnd(
    path: str | Path,
    *,
    stimulus_path: str | Path | None = None,
    subject: str | int | None = None,
    load_stimulus: bool = True,
    neural_variable: str | None = None,
) -> CNDRecording:
    """Read a CND directory or individual ``.mat`` file.

    When ``path`` is a subject file, a sibling ``dataStim<subject>.mat`` or
    ``dataStim.mat`` is inferred if ``load_stimulus`` is true. When ``path`` is
    a directory containing multiple subject files, ``subject`` is required.
    """
    source = Path(path).expanduser()
    if source.is_dir():
        data_directory = source / "dataCND" if (source / "dataCND").is_dir() else source
        neural_path = _resolve_subject_file(data_directory, subject)
        stimulus_subject = subject
        if stimulus_subject is None and neural_path is not None:
            stimulus_subject = _subject_from_filename(neural_path)
        inferred_stimulus = _resolve_stimulus_file(
            data_directory, stimulus_subject, required=False
        )
        if neural_path is not None:
            neural, additional_variables = _read_neural_file(
                neural_path, neural_variable
            )
        else:
            neural, additional_variables = None, {}
        selected_stimulus = stimulus_path or inferred_stimulus
        stimulus = (
            read_cnd_stimulus(selected_stimulus)
            if load_stimulus and selected_stimulus is not None
            else None
        )
        recording = CNDRecording(neural, stimulus, additional_variables)
        validate_cnd(recording).raise_for_errors()
        return recording

    if not source.exists():
        raise FileNotFoundError(source)

    variables = _load_mat(source)
    neural_key = _select_neural_key(variables, neural_variable, source)
    if neural_key is not None:
        neural = _parse_neural(variables[neural_key], neural_key, source)
        resolved_stimulus: Path | None = None
        if stimulus_path is not None:
            resolved_stimulus = Path(stimulus_path).expanduser()
        elif load_stimulus:
            resolved_stimulus = _resolve_stimulus_file(
                source.parent, _subject_from_filename(source), required=False
            )
        if "stim" in variables:
            stimulus = _parse_stimulus(variables["stim"], source)
        else:
            stimulus = (
                read_cnd_stimulus(resolved_stimulus)
                if resolved_stimulus is not None
                else None
            )
        additional_variables = {
            key: value
            for key, value in variables.items()
            if key not in {neural_key, "stim"}
        }
        recording = CNDRecording(neural, stimulus, additional_variables)
    elif "stim" in variables:
        recording = CNDRecording(stimulus=_parse_stimulus(variables["stim"], source))
    else:
        raise CNDReadError(f"{source} contains neither neural nor 'stim' data")

    validate_cnd(recording).raise_for_errors()
    return recording


def read_cnd_neural(path: str | Path, *, variable_name: str | None = None) -> CNDNeural:
    """Read one subject-specific CND neural file."""
    source = Path(path).expanduser()
    neural, _ = _read_neural_file(source, variable_name)
    return neural


def available_neural_variables(path: str | Path) -> tuple[str, ...]:
    """List CND recording-modality variables available in a MATLAB file."""
    source = Path(path).expanduser()
    return _find_neural_keys(_load_mat(source))


def read_cnd_stimulus(path: str | Path) -> CNDStimulus:
    """Read one CND stimulus file."""
    source = Path(path).expanduser()
    variables = _load_mat(source)
    if "stim" not in variables:
        raise CNDReadError(f"{source} does not contain a 'stim' structure")
    return _parse_stimulus(variables["stim"], source)


def write_cnd(
    recording: CNDRecording,
    destination: str | Path,
    *,
    subject: str | int = 1,
    neural_filename: str | None = None,
    stimulus_filename: str | None = None,
    overwrite: bool = False,
    compression: bool = True,
    mat_version: Literal["5", "7.3"] = "5",
) -> CNDPaths:
    """Write ``dataSubN.mat`` and/or ``dataStim.mat``.

    Both files land together, or neither does. Existing files are left alone
    unless ``overwrite=True``. Use ``mat_version="7.3"`` for big HDF5 files.
    """
    if mat_version not in {"5", "7.3"}:
        raise ValueError("mat_version must be '5' or '7.3'")
    report = validate_cnd(recording)
    report.raise_for_errors()
    output_dir = Path(destination).expanduser()
    subject_label = _canonical_subject_label(subject)
    if (
        neural_filename is None
        and recording.neural is not None
        and recording.neural.source_path is not None
        and recording.neural.source_path.name.startswith(
            ("dataParticipant_", "pre_dataSub")
        )
    ):
        neural_filename = recording.neural.source_path.name
    if (
        stimulus_filename is None
        and recording.stimulus is not None
        and recording.stimulus.source_path is not None
        and recording.stimulus.source_path.name.startswith("dataStim")
        and recording.stimulus.source_path.name != "dataStim.mat"
        and recording.stimulus.source_path.suffix == ".mat"
    ):
        stimulus_filename = recording.stimulus.source_path.name

    neural_path = (
        output_dir
        / _cnd_output_filename(
            neural_filename,
            default=f"dataSub{subject_label}.mat",
            pattern=r"(?:dataSub.+|pre_dataSub.+|dataParticipant_.+)\.mat",
            kind="neural",
        )
        if recording.neural is not None
        else None
    )
    stimulus_path = (
        output_dir
        / _cnd_output_filename(
            stimulus_filename,
            default="dataStim.mat",
            pattern=r"dataStim.*\.mat",
            kind="stimulus",
        )
        if recording.stimulus is not None
        else None
    )
    planned_paths = [path for path in (neural_path, stimulus_path) if path is not None]
    if not overwrite:
        existing = [path for path in planned_paths if path.exists()]
        if existing:
            formatted = ", ".join(str(path) for path in existing)
            raise FileExistsError(f"Refusing to overwrite {formatted}")

    output_dir.mkdir(parents=True, exist_ok=True)
    planned_outputs: list[tuple[Path, dict[str, Any]]] = []
    if recording.neural is not None:
        if neural_path is None:
            raise RuntimeError("Neural output path was not planned")
        neural_payload = dict(recording.additional_variables)
        neural_payload[recording.neural.variable_name] = _neural_to_mat(
            recording.neural
        )
        planned_outputs.append(
            (
                neural_path,
                neural_payload,
            )
        )
    if recording.stimulus is not None:
        if stimulus_path is None:
            raise RuntimeError("Stimulus output path was not planned")
        planned_outputs.append(
            (stimulus_path, {"stim": _stimulus_to_mat(recording.stimulus)})
        )
    _atomic_save_many(
        planned_outputs,
        overwrite=overwrite,
        compression=compression,
        mat_version=mat_version,
    )
    return CNDPaths(neural_path, stimulus_path)


def _load_mat(path: Path) -> dict[str, Any]:
    try:
        data = loadmat(path, simplify_cells=True)
    except NotImplementedError:
        try:
            return load_mat73(path)
        except (OSError, TypeError, ValueError) as hdf_error:
            raise CNDReadError(
                f"Could not read MATLAB v7.3/HDF5 file {path}: {hdf_error}"
            ) from hdf_error
    except (OSError, ValueError, TypeError, MatReadError) as error:
        if is_mat73(path):
            try:
                return load_mat73(path)
            except (OSError, TypeError, ValueError) as hdf_error:
                raise CNDReadError(
                    f"Could not read MATLAB v7.3/HDF5 file {path}: {hdf_error}"
                ) from hdf_error
        raise CNDReadError(f"Could not read MATLAB file {path}: {error}") from error
    workspace = data.pop("__function_workspace__", None)
    if workspace is not None:
        data = _decode_mcos_strings(data, workspace)
    return {key: value for key, value in data.items() if key not in _MATLAB_METADATA}


def _decode_mcos_strings(value: Any, workspace: Any) -> Any:
    """Resolve MATLAB MCOS string handles using the embedded v5 workspace.

    MATLAB's modern ``string`` class is stored as an opaque object plus a
    ``__function_workspace__`` byte array. SciPy intentionally exposes the
    handle. For the observed CND files, the fifth metadata word is a one-based
    index into the UTF-16LE strings in that workspace.
    """
    raw = np.asarray(workspace, dtype=np.uint8).tobytes()
    strings = tuple(
        match.group().decode("utf-16le")
        for match in re.finditer(rb"(?:[\x20-\x7e]\x00){2,}", raw)
    )
    if not strings:
        return value

    def resolve(item: Any) -> Any:
        if isinstance(item, Mapping):
            return {key: resolve(child) for key, child in item.items()}
        if isinstance(item, list):
            return [resolve(child) for child in item]
        if isinstance(item, tuple):
            return tuple(resolve(child) for child in item)
        array = np.asarray(item) if isinstance(item, np.ndarray) else None
        if array is not None and array.dtype.names:
            fields = set(array.dtype.names)
            if {"_Class", "_ObjectMetadata"} <= fields:
                class_name = str(np.asarray(array["_Class"]).ravel()[0])
                metadata_value = np.asarray(array["_ObjectMetadata"]).ravel()[0]
                metadata = np.asarray(metadata_value).ravel()
                if class_name == "string" and metadata.size >= 5:
                    index = int(metadata[4]) - 1
                    if 0 <= index < len(strings):
                        return strings[index]
            return item
        if array is not None and array.dtype == object:
            output = np.empty(array.shape, dtype=object)
            for object_index in np.ndindex(array.shape):
                output[object_index] = resolve(array[object_index])
            return output
        return item

    return resolve(value)


def _find_neural_keys(variables: Mapping[str, Any]) -> tuple[str, ...]:
    preferred = ("eeg", "meg", "nirs", "fnirs", "ieeg", "neural")
    found: list[str] = []
    for key in preferred:
        value = variables.get(key)
        if isinstance(value, Mapping) and "data" in value and "fs" in value:
            found.append(key)
    for key, value in variables.items():
        if (
            key not in found
            and key != "stim"
            and isinstance(value, Mapping)
            and {"data", "fs"} <= set(value)
        ):
            found.append(key)
    return tuple(found)


def _select_neural_key(
    variables: Mapping[str, Any], variable_name: str | None, source: Path
) -> str | None:
    keys = _find_neural_keys(variables)
    if variable_name is None:
        return keys[0] if keys else None
    if variable_name not in keys:
        available = ", ".join(keys) if keys else "none"
        raise CNDReadError(
            f"{source} has no neural variable {variable_name!r}; available: {available}"
        )
    return variable_name


def _read_neural_file(
    source: Path, variable_name: str | None
) -> tuple[CNDNeural, dict[str, Any]]:
    variables = _load_mat(source)
    key = _select_neural_key(variables, variable_name, source)
    if key is None:
        raise CNDReadError(f"{source} does not contain a recognizable neural structure")
    neural = _parse_neural(variables[key], key, source)
    additional = {
        name: value for name, value in variables.items() if name not in {key, "stim"}
    }
    return neural, additional


def _parse_neural(value: Any, variable_name: str, source: Path) -> CNDNeural:
    if not isinstance(value, Mapping):
        raise CNDReadError(f"{source}:{variable_name} is not a MATLAB structure")
    channel_value = value.get("chanlocs")
    channel_locations = _parse_channel_locations(channel_value)
    channel_locations_raw = channel_value if _is_topomap_layout(channel_value) else None
    try:
        trials, signal_types, channels_per_signal_type = _parse_neural_trials(
            value,
            channel_count_hint=(
                len(channel_locations) if channel_locations is not None else None
            ),
        )
        sfreq = float(_scalar(value["fs"]))
    except KeyError as error:
        raise CNDReadError(
            f"{source}:{variable_name} is missing {error.args[0]!r}"
        ) from error

    external_trials: tuple[np.ndarray, ...] | None = None
    external_description: str | None = None
    external_fields: dict[str, Any] = {}
    external_layout: ExternalLayout | None = None
    external_group_names: tuple[str, ...] | None = None
    external_group_channel_counts: tuple[int, ...] | None = None
    external_group_fields: tuple[dict[str, Any], ...] | None = None
    external = value.get("extChan")
    if isinstance(external, Mapping) and "data" in external:
        external_trials = _as_matrix_trial_tuple(external["data"])
        external_layout = "single_struct"
        if external.get("description") is not None:
            external_description = str(_scalar(external["description"]))
        external_fields = {
            key: item
            for key, item in external.items()
            if key not in {"data", "description"}
        }
    elif isinstance(external, Mapping):
        named_groups = _parse_named_external_groups(external, len(trials))
        if named_groups is None:
            external_fields = dict(external)
        else:
            names, group_trials, counts = named_groups
            external_trials = _combine_external_groups(
                group_trials, source, variable_name
            )
            external_description = "; ".join(names)
            external_layout = "named_fields"
            external_group_names = names
            external_group_channel_counts = counts
            external_group_fields = tuple({} for _ in names)
    elif external is not None:
        groups = [
            item
            for item in np.atleast_1d(external).ravel()
            if isinstance(item, Mapping) and "data" in item
        ]
        if groups and len(groups) == np.atleast_1d(external).size:
            group_trials = [_as_matrix_trial_tuple(group["data"]) for group in groups]
            external_trials = _combine_external_groups(
                group_trials, source, variable_name
            )
            descriptions = tuple(
                (
                    str(_scalar(group["description"]))
                    if group.get("description") is not None
                    else ""
                )
                for group in groups
            )
            external_description = "; ".join(filter(None, descriptions)) or None
            external_layout = "struct_array"
            external_group_names = descriptions
            external_group_channel_counts = tuple(
                int(trials_for_group[0].shape[1]) for trials_for_group in group_trials
            )
            external_group_fields = tuple(
                {
                    key: item
                    for key, item in group.items()
                    if key not in {"data", "description"}
                }
                for group in groups
            )
        else:
            external_fields = {"unparsedValue": external}

    original = value.get("origTrialPosition")
    original_positions = (
        tuple(int(item) for item in np.atleast_1d(original).ravel())
        if original is not None and np.asarray(original).size
        else None
    )
    data_unit = next(
        (
            str(_scalar(value[key]))
            for key in ("dataUnit", "unit", "units")
            if key in value and value[key] is not None
        ),
        None,
    )
    extras = {key: item for key, item in value.items() if key not in _NEURAL_RESERVED}
    return CNDNeural(
        trials=trials,
        sfreq=sfreq,
        data_type=_string_or_default(value.get("dataType"), variable_name.upper()),
        device_name=_optional_string(value.get("deviceName")),
        original_trial_positions=original_positions,
        channel_locations=channel_locations,
        channel_locations_raw=channel_locations_raw,
        external_trials=external_trials,
        external_description=external_description,
        external_fields=external_fields,
        external_layout=external_layout,
        external_group_names=external_group_names,
        external_group_channel_counts=external_group_channel_counts,
        external_group_fields=external_group_fields,
        rereference=value.get("reRef"),
        padding_start_sample=value.get("paddingStartSample"),
        cnd_version=_optional_scalar(value.get("cndVersion")),
        data_unit=data_unit,
        signal_types=signal_types,
        channels_per_signal_type=channels_per_signal_type,
        extra_fields=extras,
        variable_name=variable_name,
        source_path=source,
    )


def _parse_named_external_groups(
    external: Mapping[str, Any], n_trials: int
) -> tuple[tuple[str, ...], list[tuple[np.ndarray, ...]], tuple[int, ...]] | None:
    """Parse CND 1.0's ``extChan.<type> = trial-cell-array`` layout."""
    names: list[str] = []
    groups: list[tuple[np.ndarray, ...]] = []
    counts: list[int] = []
    # MATLAB v5 preserves struct-field insertion order while HDF5-backed v7.3
    # readers commonly return fields lexicographically. Canonicalize here so
    # the combined channel order is stable across MAT encodings.
    for name in sorted(external):
        value = external[name]
        try:
            trials = _as_matrix_trial_tuple(value)
        except (CNDReadError, TypeError, ValueError):
            return None
        if len(trials) != n_trials or any(trial.ndim != 2 for trial in trials):
            return None
        channel_counts = {int(trial.shape[1]) for trial in trials}
        if len(channel_counts) != 1:
            return None
        names.append(str(name))
        groups.append(trials)
        counts.append(channel_counts.pop())
    if not groups:
        return None
    return tuple(names), groups, tuple(counts)


def _combine_external_groups(
    group_trials: Sequence[tuple[np.ndarray, ...]],
    source: Path,
    variable_name: str,
) -> tuple[np.ndarray, ...]:
    if len({len(trials) for trials in group_trials}) != 1:
        raise CNDReadError(
            f"{source}:{variable_name}.extChan groups have unequal trial counts"
        )
    for trial_index in range(len(group_trials[0])):
        lengths = {int(trials[trial_index].shape[0]) for trials in group_trials}
        if len(lengths) != 1:
            raise CNDReadError(
                f"{source}:{variable_name}.extChan groups have unequal sample "
                f"counts in trial {trial_index}"
            )
    return tuple(
        np.concatenate([trials[index] for trials in group_trials], axis=1)
        for index in range(len(group_trials[0]))
    )


def _parse_neural_trials(
    value: Mapping[str, Any],
    channel_count_hint: int | None = None,
) -> tuple[tuple[np.ndarray, ...], tuple[str, ...] | None, tuple[int, ...] | None]:
    """Normalize ordinary trials and fNIRS signal-type x trial cell grids."""
    data = value["data"]
    data_type = _string_or_default(value.get("dataType"), "").strip().lower()
    datatype = value.get("datatype")
    signal_types = (
        tuple(str(item) for item in np.atleast_1d(datatype).ravel())
        if datatype is not None
        else None
    )
    array = np.asarray(data, dtype=object)
    if (
        data_type in {"fnirs", "nirs"}
        and signal_types
        and array.dtype == object
        and array.ndim == 2
        and array.shape[0] == len(signal_types)
    ):
        block_counts: list[int] = []
        for signal_index in range(len(signal_types)):
            first = np.asarray(array[signal_index, 0])
            first = first[:, np.newaxis] if first.ndim == 1 else first
            if first.ndim != 2:
                raise CNDReadError("fNIRS blocks must be time x channels")
            block_counts.append(int(first.shape[1]))
        trials: list[np.ndarray] = []
        for trial_index in range(array.shape[1]):
            blocks: list[np.ndarray] = []
            samples: int | None = None
            for signal_index, expected_channels in enumerate(block_counts):
                block = np.asarray(array[signal_index, trial_index])
                block = block[:, np.newaxis] if block.ndim == 1 else block
                if block.ndim != 2 or block.shape[1] != expected_channels:
                    raise CNDReadError("fNIRS signal blocks have inconsistent shapes")
                if samples is not None and block.shape[0] != samples:
                    raise CNDReadError("fNIRS signal blocks have unequal sample counts")
                samples = int(block.shape[0])
                blocks.append(block)
            trials.append(np.concatenate(blocks, axis=1))
        return tuple(trials), signal_types, tuple(block_counts)
    return _as_matrix_trial_tuple(data, channel_count_hint), None, None


def _parse_stimulus(value: Any, source: Path) -> CNDStimulus:
    if not isinstance(value, Mapping):
        raise CNDReadError(f"{source}:stim is not a MATLAB structure")
    required = {"data", "names", "fs"}
    missing = required - set(value)
    if missing:
        raise CNDReadError(f"{source}:stim is missing {sorted(missing)!r}")
    names = tuple(str(item) for item in np.atleast_1d(value["names"]).ravel())
    features = _as_feature_tuple(value["data"], len(names))
    stimulus_indices_value = value.get("stimIdxs")
    stimulus_indices = (
        tuple(
            _python_scalar(item)
            for item in np.atleast_1d(stimulus_indices_value).ravel()
        )
        if stimulus_indices_value is not None
        else None
    )
    condition_indices = value.get("condIdxs")
    condition_names = value.get("condNames")
    extras = {key: item for key, item in value.items() if key not in _STIMULUS_RESERVED}
    return CNDStimulus(
        names=names,
        features=features,
        sfreq=float(_scalar(value["fs"])),
        stimulus_indices=stimulus_indices,
        condition_indices=(
            tuple(
                _python_scalar(item)
                for item in np.atleast_1d(condition_indices).ravel()
            )
            if condition_indices is not None
            else None
        ),
        condition_names=(
            tuple(str(item) for item in np.atleast_1d(condition_names).ravel())
            if condition_names is not None
            else None
        ),
        cnd_version=_optional_scalar(value.get("cndVersion")),
        extra_fields=extras,
        source_path=source,
    )


def _as_trial_tuple(value: Any) -> tuple[np.ndarray, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(np.asarray(item) for item in value)
    array = np.asarray(value)
    if array.dtype == object:
        return tuple(np.asarray(item) for item in array.ravel())
    if array.ndim <= 2:
        return (array,)
    if array.ndim == 3:
        return tuple(np.asarray(array[index]) for index in range(array.shape[0]))
    raise CNDReadError(f"Cannot interpret neural data with shape {array.shape}")


def _as_matrix_trial_tuple(
    value: Any, channel_count_hint: int | None = None
) -> tuple[np.ndarray, ...]:
    """Read neural-style trials and restore squeezed one-channel matrices."""
    arrays = _as_trial_tuple(value)
    observed_counts = {
        int(array.shape[1])
        for array in arrays
        if array.ndim == 2 and array.shape[1] > 0
    }
    inferred_channels = (
        next(iter(observed_counts)) if len(observed_counts) == 1 else channel_count_hint
    )
    output: list[np.ndarray] = []
    for array in arrays:
        if array.ndim == 1 and array.size == 0 and inferred_channels is not None:
            output.append(np.empty((0, inferred_channels), dtype=array.dtype))
        elif (
            array.ndim == 1
            and inferred_channels is not None
            and inferred_channels > 1
            and array.size == inferred_channels
        ):
            output.append(array[np.newaxis, :])
        elif array.ndim == 1:
            output.append(array[:, np.newaxis])
        else:
            output.append(array)
    return tuple(output)


def _as_feature_tuple(
    value: Any, n_features: int
) -> tuple[tuple[np.ndarray, ...], ...]:
    if n_features == 0:
        return ()
    if isinstance(value, (list, tuple)):
        if n_features == 1 and (not value or not isinstance(value[0], (list, tuple))):
            return (tuple(np.asarray(item) for item in value),)
        if len(value) == n_features:
            return tuple(_as_trial_tuple(feature) for feature in value)

    array = np.asarray(value)
    if array.dtype == object:
        if array.ndim >= 2 and array.shape[0] == n_features:
            return tuple(
                tuple(
                    np.asarray(array[index, trial]) for trial in range(array.shape[1])
                )
                for index in range(n_features)
            )
        if n_features == 1:
            return (tuple(np.asarray(item) for item in array.ravel()),)
        if array.ndim == 1 and array.shape[0] == n_features:
            return tuple(_as_trial_tuple(item) for item in array)
    if n_features == 1:
        return ((array,),)
    raise CNDReadError(
        f"Cannot interpret stimulus data shape {array.shape} for {n_features} features"
    )


def _parse_channel_locations(value: Any) -> tuple[dict[str, Any], ...] | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        if _is_topomap_layout(value):
            labels = np.atleast_1d(value["label"]).ravel()
            positions = np.asarray(value["pos"])
            locations: list[dict[str, Any]] = []
            for index, label in enumerate(labels):
                name = str(label)
                if name.upper() in {"COMNT", "SCALE"}:
                    continue
                location: dict[str, Any] = {
                    "labels": name,
                    "pos": np.asarray(positions[index]),
                }
                for key in ("width", "height"):
                    optional_value = value.get(key)
                    if optional_value is None:
                        continue
                    values = np.atleast_1d(optional_value).ravel()
                    if values.size == labels.size:
                        location[key] = values[index]
                locations.append(location)
            return tuple(locations)
        lengths = [
            np.atleast_1d(item).size
            for item in value.values()
            if np.atleast_1d(item).size > 1
        ]
        if not lengths:
            return (dict(value),)
        count = max(lengths)
        columnar_locations: list[dict[str, Any]] = []
        for index in range(count):
            columnar_location: dict[str, Any] = {}
            for key, item in value.items():
                values = np.atleast_1d(item).ravel()
                columnar_location[key] = values[index] if values.size > 1 else values[0]
            columnar_locations.append(columnar_location)
        return tuple(columnar_locations)
    if isinstance(value, (list, tuple)):
        if all(isinstance(item, Mapping) for item in value):
            return tuple(dict(item) for item in value)
    # Preserve a NumPy structured dtype long enough to inspect its field names.
    # Casting to object here makes ``dtype.names`` disappear.
    array = np.asarray(value)
    if array.dtype.names:
        return tuple(
            {name: item[name] for name in array.dtype.names} for item in array.ravel()
        )
    if all(isinstance(item, Mapping) for item in array.ravel()):
        return tuple(dict(item) for item in array.ravel())
    raise CNDReadError("Could not interpret chanlocs structure")


def _is_topomap_layout(value: Any) -> bool:
    if not isinstance(value, Mapping) or not {"label", "pos"} <= set(value):
        return False
    labels = np.atleast_1d(value["label"]).ravel()
    positions = np.asarray(value["pos"])
    return positions.ndim == 2 and positions.shape[0] == labels.size


def _neural_to_mat(neural: CNDNeural) -> dict[str, Any]:
    result = dict(neural.extra_fields)
    result.update(
        {
            "dataType": neural.data_type,
            "fs": neural.sfreq,
            "data": _neural_data_to_mat(neural),
        }
    )
    if neural.device_name is not None:
        result["deviceName"] = neural.device_name
    if neural.original_trial_positions is not None:
        result["origTrialPosition"] = np.asarray(neural.original_trial_positions)
    if neural.channel_locations is not None:
        result["chanlocs"] = (
            neural.channel_locations_raw
            if neural.channel_locations_raw is not None
            else _struct_array(neural.channel_locations)
        )
    if neural.external_trials is not None:
        result["extChan"] = _external_to_mat(neural)
    elif neural.external_fields:
        result["extChan"] = dict(neural.external_fields)
    if neural.rereference is not None:
        result["reRef"] = neural.rereference
    if neural.padding_start_sample is not None:
        result["paddingStartSample"] = neural.padding_start_sample
    if neural.cnd_version is not None:
        result["cndVersion"] = neural.cnd_version
    if neural.data_unit is not None:
        result["dataUnit"] = neural.data_unit
    if neural.signal_types is not None:
        result["datatype"] = _cell_row(neural.signal_types)
    return _without_none(result)


def _external_to_mat(neural: CNDNeural) -> Any:
    trials = neural.external_trials
    if trials is None:
        raise CNDReadError("Cannot serialize absent external-channel trials")
    layout = neural.external_layout or "single_struct"
    if layout == "single_struct":
        external = dict(neural.external_fields)
        external.update(
            {
                "data": _cell_row(trials),
                "description": neural.external_description or "External channels",
            }
        )
        return external

    names = neural.external_group_names
    counts = neural.external_group_channel_counts
    if names is None or counts is None or len(names) != len(counts):
        raise CNDReadError(
            f"external_layout={layout!r} requires matching group names and counts"
        )
    if sum(counts) != int(np.asarray(trials[0]).shape[1]):
        raise CNDReadError("external group channel counts do not match external data")
    stops = np.cumsum((0, *counts))
    split_trials = tuple(
        tuple(np.asarray(trial)[:, stops[index] : stops[index + 1]] for trial in trials)
        for index in range(len(counts))
    )
    if layout == "named_fields":
        return {
            name: _cell_row(group)
            for name, group in zip(names, split_trials, strict=True)
        }
    if layout == "struct_array":
        fields = neural.external_group_fields or tuple({} for _ in names)
        if len(fields) != len(names):
            raise CNDReadError("external group metadata count does not match groups")
        groups = np.empty(len(names), dtype=object)
        for index, (name, group, metadata) in enumerate(
            zip(names, split_trials, fields, strict=True)
        ):
            item = dict(metadata)
            item["data"] = _cell_row(group)
            if name:
                item["description"] = name
            groups[index] = item
        return groups
    raise CNDReadError(f"Unsupported external channel layout {layout!r}")


def _neural_data_to_mat(neural: CNDNeural) -> np.ndarray:
    if neural.signal_types is None:
        return _cell_row(neural.trials)
    counts = neural.channels_per_signal_type
    if counts is None or len(counts) != len(neural.signal_types):
        raise CNDReadError("signal_types require matching channels_per_signal_type")
    data = np.empty((len(counts), neural.n_trials), dtype=object)
    stops = np.cumsum((0, *counts))
    for signal_index in range(len(counts)):
        for trial_index, trial in enumerate(neural.trials):
            data[signal_index, trial_index] = np.asarray(trial)[
                :, stops[signal_index] : stops[signal_index + 1]
            ]
    return data


def _stimulus_to_mat(stimulus: CNDStimulus) -> dict[str, Any]:
    result = dict(stimulus.extra_fields)
    data = np.empty((stimulus.n_features, stimulus.n_trials), dtype=object)
    for feature_index, trials in enumerate(stimulus.features):
        for trial_index, trial in enumerate(trials):
            data[feature_index, trial_index] = np.asarray(trial)
    result.update(
        {
            "names": _cell_row(stimulus.names),
            "data": data,
            "fs": stimulus.sfreq,
        }
    )
    if stimulus.stimulus_indices is not None:
        result["stimIdxs"] = _sequence_to_mat(stimulus.stimulus_indices)
    if stimulus.condition_indices is not None:
        result["condIdxs"] = _sequence_to_mat(stimulus.condition_indices)
    if stimulus.condition_names is not None:
        result["condNames"] = _cell_row(stimulus.condition_names)
    if stimulus.cnd_version is not None:
        result["cndVersion"] = stimulus.cnd_version
    return _without_none(result)


def _cell_row(values: Sequence[Any]) -> np.ndarray:
    cell = np.empty((1, len(values)), dtype=object)
    for index, value in enumerate(values):
        cell[0, index] = value
    return cell


def _sequence_to_mat(values: Sequence[Any]) -> np.ndarray:
    if any(isinstance(value, (str, np.str_)) for value in values):
        return _cell_row(values)
    return np.asarray(values)


def _struct_array(records: Sequence[Mapping[str, Any]]) -> np.ndarray:
    fields = sorted({key for record in records for key in record})
    dtype = [(field, object) for field in fields]
    output = np.empty((1, len(records)), dtype=dtype)
    for index, record in enumerate(records):
        for field in fields:
            output[field][0, index] = _matlab_value(record.get(field))
    return output


def _matlab_value(value: Any) -> Any:
    if value is None:
        return np.empty((0, 0))
    return value


def _without_none(mapping: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: _matlab_value(value) for key, value in mapping.items() if value is not None
    }


def _atomic_savemat(
    path: Path,
    payload: dict[str, Any],
    overwrite: bool,
    compression: bool,
    *,
    mat_version: Literal["5", "7.3"] = "5",
) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _prepare_mat(path, payload, compression, mat_version=mat_version)
    try:
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _prepare_mat(
    path: Path,
    payload: dict[str, Any],
    compression: bool,
    *,
    mat_version: Literal["5", "7.3"],
) -> Path:
    """Serialize one MAT payload beside its destination without publishing it."""
    handle = tempfile.NamedTemporaryFile(
        prefix=f".{path.stem}.", suffix=".mat", dir=path.parent, delete=False
    )
    temporary = Path(handle.name)
    handle.close()
    try:
        if mat_version == "5":
            savemat(
                temporary,
                payload,
                appendmat=False,
                do_compression=compression,
                long_field_names=True,
            )
        else:
            hdf5storage.savemat(
                temporary,
                payload,
                appendmat=False,
                fmt="7.3",
                oned_as="row",
                store_python_metadata=False,
                truncate_existing=True,
                compress=compression,
            )
        return temporary
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _atomic_save_many(
    outputs: Sequence[tuple[Path, dict[str, Any]]],
    *,
    overwrite: bool,
    compression: bool,
    mat_version: Literal["5", "7.3"],
) -> None:
    """Publish a neural/stimulus file set together, rolling back on failure."""
    if not outputs:
        return
    if not overwrite:
        existing = [path for path, _ in outputs if path.exists()]
        if existing:
            formatted = ", ".join(str(path) for path in existing)
            raise FileExistsError(f"Refusing to overwrite {formatted}")

    prepared: list[tuple[Path, Path]] = []
    backups: list[tuple[Path, Path]] = []
    published: list[Path] = []
    try:
        # Complete every potentially expensive serialization before touching
        # any existing destination file.
        for path, payload in outputs:
            prepared.append(
                (
                    path,
                    _prepare_mat(path, payload, compression, mat_version=mat_version),
                )
            )
        for path, temporary in prepared:
            if path.exists():
                backup_handle = tempfile.NamedTemporaryFile(
                    prefix=f".{path.stem}.",
                    suffix=".backup",
                    dir=path.parent,
                    delete=False,
                )
                backup = Path(backup_handle.name)
                backup_handle.close()
                backup.unlink()
                os.replace(path, backup)
                backups.append((path, backup))
            os.replace(temporary, path)
            published.append(path)
    except Exception:
        for path in reversed(published):
            path.unlink(missing_ok=True)
        for path, backup in reversed(backups):
            if backup.exists():
                os.replace(backup, path)
        raise
    finally:
        for _, temporary in prepared:
            temporary.unlink(missing_ok=True)
        for _, backup in backups:
            backup.unlink(missing_ok=True)


def _resolve_subject_file(directory: Path, subject: str | int | None) -> Path | None:
    if subject is not None:
        subject_candidates = (
            directory / f"dataSub{subject}.mat",
            directory / f"pre_dataSub{subject}.mat",
            directory / f"dataParticipant_{subject}.mat",
        )
        for candidate in subject_candidates:
            if candidate.exists():
                return candidate
        raise FileNotFoundError(subject_candidates[0])
    candidates = sorted(
        {
            *directory.glob("dataSub*.mat"),
            *directory.glob("pre_dataSub*.mat"),
            *directory.glob("dataParticipant_*.mat"),
        }
    )
    if not candidates:
        return None
    if len(candidates) > 1:
        raise CNDReadError(
            f"{directory} contains {len(candidates)} subject files; pass subject=..."
        )
    return candidates[0]


def _resolve_stimulus_file(
    directory: Path,
    subject: str | int | None,
    *,
    required: bool,
) -> Path | None:
    candidates: Iterable[Path]
    search_directories = [directory]
    sibling_stimulus = directory.parent / "stimCND"
    if sibling_stimulus.is_dir():
        search_directories.append(sibling_stimulus)
    if directory.parent not in search_directories:
        search_directories.append(directory.parent)
    candidate_names = (
        (f"dataStim{subject}.mat", f"dataStim_{subject}.mat", "dataStim.mat")
        if subject is not None
        else ("dataStim.mat",)
    )
    candidates = (
        search_directory / name
        for search_directory in search_directories
        for name in candidate_names
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    if required:
        raise FileNotFoundError(directory / "dataStim.mat")
    return None


def _subject_from_filename(path: Path) -> str | None:
    stem = path.stem
    if stem.startswith("dataSub"):
        return stem.removeprefix("dataSub")
    if stem.startswith("pre_dataSub"):
        return stem.removeprefix("pre_dataSub")
    if stem.startswith("dataParticipant_"):
        return stem.removeprefix("dataParticipant_")
    return None


def _scalar(value: Any) -> Any:
    array = np.asarray(value)
    return array.item() if array.size == 1 else value


def _optional_string(value: Any) -> str | None:
    return None if value is None else str(_scalar(value))


def _optional_scalar(value: Any) -> Any:
    if value is None:
        return None
    return _python_scalar(_scalar(value))


def _string_or_default(value: Any, default: str) -> str:
    scalar = _scalar(value) if value is not None else None
    if isinstance(scalar, (str, np.str_)):
        return str(scalar)
    return default


def _python_scalar(value: Any) -> Any:
    return value.item() if isinstance(value, np.generic) else value


def _canonical_subject_label(subject: str | int) -> str:
    value = str(subject)
    if not value.isdigit() or int(value) < 1:
        raise ValueError("subject must be a positive numeric CND index")
    return str(int(value))


def _cnd_output_filename(
    filename: str | None, *, default: str, pattern: str, kind: str
) -> str:
    value = default if filename is None else filename
    if Path(value).name != value or re.fullmatch(pattern, value) is None:
        raise ValueError(f"{kind}_filename is not a recognised CND .mat filename")
    return value
