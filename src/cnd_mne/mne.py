"""CND recordings as MNE objects, and back."""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

import mne
import numpy as np

from .exceptions import CNDAmbiguousUnitError, CNDUnsupportedError, CNDValidationError
from .model import (
    CNDNeural,
    CNDPaths,
    CNDRecording,
    CNDStimulus,
    CNDTrialMetadata,
    CNDVersion,
)
from .validation import validate_cnd

MontagePolicy = Literal["none", "eeglab"]
UnsupportedMetadataPolicy = Literal["warn", "raise", "ignore"]

_UNIT_TO_VOLTS = {
    "v": 1.0,
    "volt": 1.0,
    "volts": 1.0,
    "mv": 1e-3,
    "millivolt": 1e-3,
    "millivolts": 1e-3,
    "uv": 1e-6,
    "microvolt": 1e-6,
    "microvolts": 1e-6,
    "nv": 1e-9,
    "nanovolt": 1e-9,
    "nanovolts": 1e-9,
}
_UNIT_TO_MOLAR = {
    "m": 1.0,
    "molar": 1.0,
    "mol/l": 1.0,
    "mm": 1e-3,
    "mmolar": 1e-3,
    "mmol/l": 1e-3,
    "um": 1e-6,
    "umolar": 1e-6,
    "umol/l": 1e-6,
    "nm": 1e-9,
    "nmolar": 1e-9,
    "nmol/l": 1e-9,
}


@dataclass(slots=True)
class MNECNDRecording:
    """One MNE ``Raw`` per trial, plus the original CND on ``cnd``."""

    raws: tuple[mne.io.RawArray, ...]
    cnd: CNDRecording
    neural_unit: str

    @property
    def stimulus(self) -> CNDStimulus | None:
        return self.cnd.stimulus

    @property
    def trial_metadata(self) -> tuple[CNDTrialMetadata, ...]:
        """Trial metadata in the same order as ``raws``."""
        return self.cnd.trial_metadata

    @property
    def trial_slices(self) -> tuple[slice, ...]:
        """Sample slices of each trial after :meth:`concatenate`."""
        start = 0
        output: list[slice] = []
        for raw in self.raws:
            stop = start + raw.n_times
            output.append(slice(start, stop))
            start = stop
        return tuple(output)

    def concatenate(self, *, add_trial_annotations: bool = True) -> mne.io.BaseRaw:
        """Glue trials into one ``Raw``. Joins are fake; MNE marks them.

        Copies the per-trial objects. Optional ``CND_TRIAL/N`` annotations
        mark each trial start.
        """
        if not self.raws:
            raise CNDValidationError("Cannot concatenate an empty CND recording")
        combined = mne.concatenate_raws(
            [raw.copy() for raw in self.raws], preload=True, verbose="ERROR"
        )
        if add_trial_annotations:
            sfreq = float(combined.info["sfreq"])
            onsets = [trial_slice.start / sfreq for trial_slice in self.trial_slices]
            annotations = mne.Annotations(
                onset=onsets,
                duration=[0.0] * len(onsets),
                description=[
                    f"CND_TRIAL/{metadata.cnd_index}"
                    for metadata in self.trial_metadata
                ],
            )
            combined.set_annotations(combined.annotations + annotations)
        return combined

    def stimulus_raws(self, feature: str | int) -> tuple[mne.io.RawArray, ...]:
        """One stimulus feature as ``misc`` channels. Same rate and values.

        A spectrogram becomes one channel per bin. No resampling or unit claim.
        """
        stimulus = self.stimulus
        if stimulus is None:
            raise CNDValidationError("CND recording has no stimulus data")
        feature_index = _feature_index(stimulus, feature)
        feature_name = stimulus.names[feature_index]
        output: list[mne.io.RawArray] = []
        for trial in stimulus.features[feature_index]:
            array = np.asarray(trial, dtype=np.float64)
            if array.ndim == 1:
                array = array[:, np.newaxis]
            if array.ndim != 2:
                raise CNDValidationError(
                    f"Stimulus feature {feature_name!r} must be time x dimensions"
                )
            if array.shape[1] == 1:
                names = [feature_name]
            else:
                width = max(2, len(str(array.shape[1])))
                names = [
                    f"{feature_name}[{index:0{width}d}]"
                    for index in range(1, array.shape[1] + 1)
                ]
            info = mne.create_info(
                names, stimulus.sfreq, ch_types=["misc"] * len(names)
            )
            info["description"] = "Imported CND stimulus feature; arbitrary units"
            output.append(mne.io.RawArray(array.T, info, verbose="ERROR"))
        return tuple(output)

    def stimulus_annotations(
        self,
        feature: str | int,
        *,
        threshold: float = 0.0,
        include_values: bool = False,
    ) -> tuple[mne.Annotations, ...]:
        """Turn a sparse 1-D feature (word onsets, etc.) into annotations.

        Samples above ``threshold`` become zero-length marks on the stimulus
        clock. Continuous / multi-D features are rejected.
        """
        stimulus = self.stimulus
        if stimulus is None:
            raise CNDValidationError("CND recording has no stimulus data")
        if not np.isfinite(threshold) or threshold < 0:
            raise ValueError("threshold must be a finite non-negative number")
        feature_index = _feature_index(stimulus, feature)
        feature_name = stimulus.names[feature_index]
        output: list[mne.Annotations] = []
        for trial in stimulus.features[feature_index]:
            values = np.asarray(trial, dtype=np.float64)
            if values.ndim == 2 and values.shape[1] == 1:
                values = values[:, 0]
            if values.ndim != 1:
                raise CNDValidationError(
                    f"Stimulus feature {feature_name!r} must be one-dimensional "
                    "to create annotations"
                )
            indices = np.flatnonzero(np.abs(values) > threshold)
            if include_values:
                descriptions = [
                    f"CND_STIM/{feature_name}/{values[index]:g}" for index in indices
                ]
            else:
                descriptions = [f"CND_STIM/{feature_name}"] * len(indices)
            output.append(
                mne.Annotations(
                    onset=indices.astype(float) / stimulus.sfreq,
                    duration=np.zeros(len(indices)),
                    description=descriptions,
                )
            )
        return tuple(output)

    def external_raws(
        self,
        *,
        unit: str,
        channel_types: str | Sequence[str] | None = None,
        channel_names: Sequence[str] | None = None,
    ) -> tuple[mne.io.RawArray, ...]:
        """Extra CND channels (EOG, mastoids, …) as their own ``Raw`` objects.

        Pass ``unit``. Optionally pass ``channel_types`` such as ``"eog"``.
        """
        neural = self.cnd.neural
        if neural is None or neural.external_trials is None:
            raise CNDValidationError("CND recording has no external-channel data")
        first = np.asarray(neural.external_trials[0])
        if first.ndim != 2:
            raise CNDValidationError("CND external trials must be time x channels")
        n_channels = int(first.shape[1])
        stored_names = neural.external_fields.get("channelNames")
        stored_types = neural.external_fields.get("channelTypes")
        names = tuple(
            str(name)
            for name in (
                channel_names
                if channel_names is not None
                else np.atleast_1d(stored_names).ravel()
                if stored_names is not None
                else tuple(f"EXT{index:03d}" for index in range(1, n_channels + 1))
            )
        )
        types = (
            (channel_types,) * n_channels
            if isinstance(channel_types, str)
            else tuple(channel_types)
            if channel_types is not None
            else tuple(str(value) for value in np.atleast_1d(stored_types).ravel())
            if stored_types is not None
            else ("misc",) * n_channels
        )
        if len(names) != n_channels or len(types) != n_channels:
            raise CNDValidationError(
                "external channel names/types must match the external channel count"
            )
        if len(set(names)) != len(names):
            raise CNDValidationError("external channel names must be unique")
        scale = _unit_scale(unit, "eeg")
        info = mne.create_info(list(names), neural.sfreq, ch_types=list(types))
        info["description"] = (
            "Imported CND external channels; "
            f"source_unit={_canonical_unit(unit, 'eeg')}; "
            f"source_description={neural.external_description or 'unspecified'}"
        )
        output: list[mne.io.RawArray] = []
        for index, trial in enumerate(neural.external_trials):
            array = np.asarray(trial, dtype=np.float64)
            if array.ndim != 2 or array.shape[1] != n_channels:
                raise CNDValidationError(
                    f"CND external trial {index} has inconsistent channel shape"
                )
            output.append(
                mne.io.RawArray(array.T * scale, info.copy(), verbose="ERROR")
            )
        return tuple(output)

    def to_cnd(
        self,
        *,
        output_unit: str | None = None,
        cnsp_external_cells: bool = False,
        on_unsupported_metadata: UnsupportedMetadataPolicy = "warn",
    ) -> CNDRecording:
        """Export edited MNE values while preserving the CND template.

        Set ``cnsp_external_cells`` to wrap a legacy single external group in
        a MATLAB cell for CNSP scripts that use ``eeg.extChan{1}``.
        """
        return from_mne(
            self.raws,
            template=self.cnd,
            output_unit=output_unit or self.neural_unit,
            cnsp_external_cells=cnsp_external_cells,
            on_unsupported_metadata=on_unsupported_metadata,
        )

    def write_cnd(
        self,
        destination: str | Path,
        *,
        subject: str | int = 1,
        output_unit: str | None = None,
        cnsp_external_cells: bool = False,
        overwrite: bool = False,
        compression: bool = True,
        mat_version: Literal["5", "7.3"] = "5",
        preserve_source_filenames: bool = True,
        on_unsupported_metadata: UnsupportedMetadataPolicy = "warn",
    ) -> CNDPaths:
        """Export edited MNE values and atomically write a CND directory."""
        from .io import write_cnd

        recording = self.to_cnd(
            output_unit=output_unit,
            cnsp_external_cells=cnsp_external_cells,
            on_unsupported_metadata=on_unsupported_metadata,
        )
        neural_filename = None
        stimulus_filename = None
        if preserve_source_filenames:
            if self.cnd.neural is not None and self.cnd.neural.source_path is not None:
                name = self.cnd.neural.source_path.name
                if name.startswith(("dataParticipant_", "pre_dataSub")):
                    neural_filename = name
            if (
                self.cnd.stimulus is not None
                and self.cnd.stimulus.source_path is not None
                and self.cnd.stimulus.source_path.name.startswith("dataStim")
                and self.cnd.stimulus.source_path.name != "dataStim.mat"
                and self.cnd.stimulus.source_path.suffix == ".mat"
            ):
                stimulus_filename = self.cnd.stimulus.source_path.name
        return write_cnd(
            recording,
            destination,
            subject=subject,
            neural_filename=neural_filename,
            stimulus_filename=stimulus_filename,
            overwrite=overwrite,
            compression=compression,
            mat_version=mat_version,
        )


def read_cnd_mne(
    path: str | Path,
    *,
    stimulus_path: str | Path | None = None,
    subject: str | int | None = None,
    load_stimulus: bool = True,
    neural_variable: str | None = None,
    neural_unit: str | None = None,
    montage: MontagePolicy = "none",
    coordinate_scale_to_meters: float | None = None,
) -> MNECNDRecording:
    """Read CND MATLAB files into one MNE ``Raw`` per trial."""
    from .io import read_cnd

    recording = read_cnd(
        path,
        stimulus_path=stimulus_path,
        subject=subject,
        load_stimulus=load_stimulus,
        neural_variable=neural_variable,
    )
    return to_mne(
        recording,
        neural_unit=neural_unit,
        montage=montage,
        coordinate_scale_to_meters=coordinate_scale_to_meters,
    )


def to_mne(
    recording: CNDRecording,
    *,
    neural_unit: str | None = None,
    montage: MontagePolicy = "none",
    coordinate_scale_to_meters: float | None = None,
) -> MNECNDRecording:
    """Create one MNE ``RawArray`` per variable-length CND neural trial.

    Parameters
    ----------
    recording
        CND data.
    neural_unit
        Physical unit of the numerical CND EEG values. Required unless the CND
        file declares ``dataUnit``, ``unit``, or ``units``. MNE stores EEG in
        volts.
    montage
        ``"none"`` (default) avoids guessing coordinate semantics.
        ``"eeglab"`` applies the axis mapping used by existing CND importers:
        MNE XYZ = ``(-CND.Y, CND.X, CND.Z)``.
    coordinate_scale_to_meters
        Multiplier that converts stored coordinates to metres. Required when
        ``montage="eeglab"``; for example, ``0.01`` for centimetres.
    """
    report = validate_cnd(recording)
    report.raise_for_errors()
    neural = recording.neural
    if neural is None:
        raise CNDValidationError("CND recording has no neural data")
    data_type = neural.data_type.strip().lower()
    if data_type not in {"eeg", "fnirs", "nirs"}:
        raise CNDUnsupportedError(
            f"MNE adapter supports EEG and fNIRS, not {neural.data_type!r}"
        )

    unit = neural_unit or neural.data_unit
    if unit is None:
        raise CNDAmbiguousUnitError(
            "CND does not declare the neural unit; pass neural_unit explicitly"
        )
    scale = _unit_scale(unit, data_type)
    ch_names, ch_types = _channel_spec(neural)
    if neural.channel_names is None:
        warnings.warn(
            "CND has no complete channel labels; generated stable names "
            "and omitted montage",
            RuntimeWarning,
            stacklevel=2,
        )
        montage = "none"

    if len(set(ch_names)) != len(ch_names):
        raise CNDValidationError("CND channel labels are not unique")
    info = mne.create_info(list(ch_names), neural.sfreq, ch_types=list(ch_types))
    info["description"] = _description(neural)

    dig_montage = _make_montage(
        neural,
        ch_names,
        montage=montage,
        coordinate_scale_to_meters=coordinate_scale_to_meters,
    )
    raws: list[mne.io.RawArray] = []
    for trial in neural.trials:
        data_mne_units = np.asarray(trial, dtype=np.float64).T * scale
        raw = mne.io.RawArray(data_mne_units, info.copy(), verbose="ERROR")
        if dig_montage is not None:
            raw.set_montage(dig_montage, on_missing="raise", verbose="ERROR")
        raws.append(raw)
    return MNECNDRecording(tuple(raws), recording, _canonical_unit(unit, data_type))


def from_mne(
    raws: mne.io.BaseRaw | Sequence[mne.io.BaseRaw],
    *,
    stimulus: CNDStimulus | None = None,
    external_raws: mne.io.BaseRaw | Sequence[mne.io.BaseRaw] | None = None,
    external_unit: str | None = None,
    external_description: str | None = None,
    cnsp_external_cells: bool = False,
    output_unit: str = "V",
    device_name: str | None = None,
    original_trial_positions: Sequence[int] | None = None,
    cnd_version: CNDVersion | None = 1.0,
    template: CNDRecording | None = None,
    on_unsupported_metadata: UnsupportedMetadataPolicy = "warn",
) -> CNDRecording:
    """Build CND from one or more MNE ``Raw`` objects.

    MNE stores EEG in volts. ``output_unit`` is what gets written to CND.
    Pass stimulus data yourself; MNE cannot invent envelopes. Auxiliary channels
    such as EOG can be passed separately through ``external_raws``. Use
    ``template`` (or :meth:`MNECNDRecording.to_cnd`) to keep leftover CND fields.
    New external inputs use MATLAB cell groups. Set ``cnsp_external_cells=True``
    to also normalize a legacy template single-group struct to that layout;
    the default preserves the template layout.
    """
    raw_trials = (raws,) if isinstance(raws, mne.io.BaseRaw) else tuple(raws)
    if not raw_trials:
        raise CNDValidationError("At least one MNE Raw object is required")
    if on_unsupported_metadata not in {"warn", "raise", "ignore"}:
        raise ValueError("on_unsupported_metadata must be 'warn', 'raise', or 'ignore'")
    _handle_unsupported_mne_metadata(raw_trials, on_unsupported_metadata)

    external_trials_raw = (
        ()
        if external_raws is None
        else (external_raws,)
        if isinstance(external_raws, mne.io.BaseRaw)
        else tuple(external_raws)
    )
    if external_trials_raw and external_unit is None:
        raise CNDAmbiguousUnitError(
            "external_unit is required when exporting external_raws"
        )
    _handle_unsupported_mne_metadata(external_trials_raw, on_unsupported_metadata)

    first = raw_trials[0]
    sfreq = float(first.info["sfreq"])
    ch_names = tuple(first.ch_names)
    ch_types = tuple(first.get_channel_types())
    template_neural = template.neural if template is not None else None
    if template is not None and template_neural is None:
        raise CNDValidationError("CND template has no neural data")
    template_data_type = (
        template_neural.data_type.strip().lower()
        if template_neural is not None
        else "eeg"
    )
    allowed_types = (
        {"hbo", "hbr", "misc"} if template_data_type in {"fnirs", "nirs"} else {"eeg"}
    )
    if any(channel_type not in allowed_types for channel_type in ch_types):
        raise CNDUnsupportedError(
            f"Exporter for {template_data_type!r} does not support channel types "
            f"{sorted(set(ch_types) - allowed_types)!r}"
        )
    for index, raw in enumerate(raw_trials[1:], start=1):
        if not np.isclose(float(raw.info["sfreq"]), sfreq, rtol=0, atol=1e-12):
            raise CNDValidationError(f"MNE trial {index} has a different sampling rate")
        if tuple(raw.ch_names) != ch_names:
            raise CNDValidationError(
                f"MNE trial {index} has different channel names/order"
            )
        if tuple(raw.get_channel_types()) != ch_types:
            raise CNDValidationError(f"MNE trial {index} has different channel types")

    external_trials: tuple[np.ndarray, ...] | None = None
    external_names: tuple[str, ...] | None = None
    external_types: tuple[str, ...] | None = None
    if external_trials_raw:
        if len(external_trials_raw) != len(raw_trials):
            raise CNDValidationError(
                "external_raws trial count does not match neural trial count"
            )
        external_names = tuple(external_trials_raw[0].ch_names)
        external_types = tuple(external_trials_raw[0].get_channel_types())
        external_scale = _unit_scale(str(external_unit), "eeg")
        converted_external: list[np.ndarray] = []
        for index, (raw, external) in enumerate(
            zip(raw_trials, external_trials_raw, strict=True)
        ):
            if not np.isclose(float(external.info["sfreq"]), sfreq, rtol=0, atol=1e-12):
                raise CNDValidationError(
                    f"MNE external trial {index} has a different sampling rate"
                )
            if (
                external.first_samp != raw.first_samp
                or external.info["meas_date"] != raw.info["meas_date"]
            ):
                raise CNDValidationError(
                    f"MNE external trial {index} has a different time origin"
                )
            if external.n_times != raw.n_times:
                raise CNDValidationError(
                    f"MNE external trial {index} has a different sample count"
                )
            if tuple(external.ch_names) != external_names:
                raise CNDValidationError(
                    f"MNE external trial {index} has different channel names/order"
                )
            if tuple(external.get_channel_types()) != external_types:
                raise CNDValidationError(
                    f"MNE external trial {index} has different channel types"
                )
            converted_external.append(external.get_data().T / external_scale)
        external_trials = tuple(converted_external)

    if template_neural is not None:
        if len(raw_trials) != template_neural.n_trials:
            raise CNDValidationError("MNE trial count does not match the CND template")
        template_names, template_types = _channel_spec(template_neural)
        if ch_names != template_names:
            raise CNDValidationError(
                "MNE channel names/order do not match the CND template"
            )
        if ch_types != template_types:
            raise CNDValidationError("MNE channel types do not match the CND template")
        for index, (raw, source_trial) in enumerate(
            zip(raw_trials, template_neural.trials, strict=True)
        ):
            if raw.n_times != np.asarray(source_trial).shape[0]:
                raise CNDValidationError(
                    f"MNE trial {index} length does not match the CND template; "
                    "supply synchronized replacement stimulus/external data through "
                    "a new CND recording instead"
                )

    mne_units_per_output_unit = _unit_scale(output_unit, template_data_type)
    trials = tuple(raw.get_data().T / mne_units_per_output_unit for raw in raw_trials)
    if original_trial_positions is None and template_neural is not None:
        original = template_neural.original_trial_positions
    elif original_trial_positions is None:
        original = tuple(range(1, len(raw_trials) + 1))
    else:
        original = tuple(int(value) for value in original_trial_positions)
    if original is not None and len(original) != len(raw_trials):
        raise CNDValidationError(
            "original_trial_positions length does not match MNE trial count"
        )

    if template_neural is not None:
        if template is None:
            raise CNDValidationError("Internal template state is inconsistent")
        neural = replace(
            template_neural,
            trials=trials,
            sfreq=sfreq,
            device_name=device_name or template_neural.device_name,
            original_trial_positions=original,
            data_unit=_canonical_unit(output_unit, template_data_type),
            external_trials=(
                external_trials
                if external_trials is not None
                else template_neural.external_trials
            ),
            external_description=(
                external_description
                if external_trials is not None
                else template_neural.external_description
            ),
            external_fields=(
                {
                    "channelNames": np.asarray(external_names, dtype=object),
                    "channelTypes": np.asarray(external_types, dtype=object),
                    "dataUnit": _canonical_unit(str(external_unit), "eeg"),
                }
                if external_trials is not None
                else template_neural.external_fields
            ),
            external_layout=(
                "single_struct"
                if external_trials is not None
                else template_neural.external_layout
            ),
            source_path=None,
        )
        resolved_stimulus = stimulus if stimulus is not None else template.stimulus
    else:
        positions = _extract_channel_locations(first)
        extras: dict[str, object] = {}
        if positions is not None:
            extras["coordUnit"] = "m"
            extras["coordTransform"] = "MNE-head-to-EEGLAB-axis"
        neural = CNDNeural(
            trials=trials,
            sfreq=sfreq,
            data_type="EEG",
            device_name=device_name,
            original_trial_positions=original,
            channel_locations=positions or tuple({"labels": name} for name in ch_names),
            external_trials=external_trials,
            external_description=external_description,
            external_fields=(
                {
                    "channelNames": np.asarray(external_names, dtype=object),
                    "channelTypes": np.asarray(external_types, dtype=object),
                    "dataUnit": _canonical_unit(str(external_unit), "eeg"),
                }
                if external_trials is not None
                else {}
            ),
            external_layout=("single_struct" if external_trials is not None else None),
            cnd_version=cnd_version,
            data_unit=_canonical_unit(output_unit, "eeg"),
            extra_fields=extras,
            variable_name="eeg",
        )
        resolved_stimulus = stimulus
    if (external_trials is not None or cnsp_external_cells) and (
        neural.external_trials is not None and neural.external_layout == "single_struct"
    ):
        # scipy simplifies a singleton MATLAB cell to its contained struct.
        # Canonicalise single-group MNE exports so CNSP brace indexing survives.
        neural = replace(
            neural,
            external_layout="struct_array",
            external_group_names=(neural.external_description or "External channels",),
            external_group_channel_counts=(int(neural.external_trials[0].shape[1]),),
            external_group_fields=(dict(neural.external_fields),),
        )
    recording = CNDRecording(
        neural,
        resolved_stimulus,
        dict(template.additional_variables) if template is not None else {},
    )
    validate_cnd(recording).raise_for_errors()
    return recording


def _channel_spec(neural: CNDNeural) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Channel names and MNE types for this CND signal."""
    data_type = neural.data_type.strip().lower()
    if data_type == "eeg":
        eeg_names = neural.channel_names or tuple(
            f"EEG{index:03d}" for index in range(1, neural.n_channels + 1)
        )
        return eeg_names, ("eeg",) * neural.n_channels
    if data_type not in {"fnirs", "nirs"}:
        raise CNDUnsupportedError(f"Unsupported neural type {neural.data_type!r}")
    signal_types = neural.signal_types
    counts = neural.channels_per_signal_type
    if signal_types is None or counts is None:
        raise CNDValidationError(
            "fNIRS conversion requires signal_types and channels_per_signal_type"
        )
    fnirs_names: list[str] = []
    channel_types: list[str] = []
    for signal_type, count in zip(signal_types, counts, strict=True):
        normalized = _normalize_unit(signal_type)
        if normalized in {"hbo", "oxy", "oxyhemoglobin"}:
            mne_type = "hbo"
            prefix = "HbO"
        elif normalized in {"hbr", "deoxy", "deoxyhemoglobin"}:
            mne_type = "hbr"
            prefix = "HbR"
        else:
            # MNE has no HbT channel type. Keep it visible as misc while its
            # molar numerical scale and original CND datatype are preserved.
            mne_type = "misc"
            prefix = str(signal_type).strip() or "fNIRS"
        width = max(2, len(str(count)))
        fnirs_names.extend(
            f"{prefix}{index:0{width}d}" for index in range(1, count + 1)
        )
        channel_types.extend([mne_type] * count)
    return tuple(fnirs_names), tuple(channel_types)


def _feature_index(stimulus: CNDStimulus, feature: str | int) -> int:
    if isinstance(feature, str):
        try:
            return stimulus.names.index(feature)
        except ValueError as error:
            raise KeyError(feature) from error
    feature_index = int(feature)
    if not 0 <= feature_index < stimulus.n_features:
        raise IndexError(feature_index)
    return feature_index


def _make_montage(
    neural: CNDNeural,
    ch_names: Sequence[str],
    *,
    montage: MontagePolicy,
    coordinate_scale_to_meters: float | None,
) -> mne.channels.DigMontage | None:
    if montage == "none":
        return None
    if montage != "eeglab":
        raise ValueError(f"Unknown montage policy {montage!r}")
    if coordinate_scale_to_meters is None or coordinate_scale_to_meters <= 0:
        raise CNDValidationError(
            "montage='eeglab' requires a positive coordinate_scale_to_meters"
        )
    if neural.channel_locations is None:
        return None
    positions: dict[str, np.ndarray] = {}
    for name, location in zip(ch_names, neural.channel_locations, strict=True):
        try:
            x = float(location["X"])
            y = float(location["Y"])
            z = float(location["Z"])
        except (KeyError, TypeError, ValueError):
            raise CNDValidationError(
                f"Channel {name!r} lacks numeric X/Y/Z coordinates"
            ) from None
        position = np.array([-y, x, z], dtype=float) * coordinate_scale_to_meters
        if not np.all(np.isfinite(position)):
            raise CNDValidationError(f"Channel {name!r} has non-finite coordinates")
        positions[name] = position

    biosemi_name = _matching_biosemi_montage(neural, ch_names)
    if biosemi_name is not None:
        median_radius = float(
            np.median([np.linalg.norm(position) for position in positions.values()])
        )
        if not 0.05 <= median_radius <= 0.11:
            raise CNDValidationError(
                "BioSemi coordinates have an implausible median head radius of "
                f"{median_radius:.6g} m; check coordinate_scale_to_meters"
            )
        template = mne.channels.make_standard_montage(
            biosemi_name, head_size=median_radius
        )
        native_head_t = mne.channels.compute_native_head_t(template, on_missing="raise")
        head_positions = {
            name: mne.transforms.apply_trans(native_head_t, position)
            for name, position in positions.items()
        }
        template_positions = template.get_positions()
        fiducials = {
            name: mne.transforms.apply_trans(native_head_t, template_positions[name])
            for name in ("nasion", "lpa", "rpa")
        }
        return mne.channels.make_dig_montage(
            ch_pos=head_positions,
            nasion=fiducials["nasion"],
            lpa=fiducials["lpa"],
            rpa=fiducials["rpa"],
            coord_frame="head",
        )
    return mne.channels.make_dig_montage(ch_pos=positions, coord_frame="head")


def _matching_biosemi_montage(neural: CNDNeural, ch_names: Sequence[str]) -> str | None:
    """Return an exact MNE BioSemi template match for declared BioSemi data."""
    if "biosemi" not in (neural.device_name or "").lower():
        return None
    for candidate in (
        "biosemi16",
        "biosemi32",
        "biosemi64",
        "biosemi128",
        "biosemi160",
        "biosemi256",
    ):
        template = mne.channels.make_standard_montage(candidate, head_size=0.095)
        if set(ch_names) == set(template.ch_names):
            return candidate
    return None


def _extract_channel_locations(
    raw: mne.io.BaseRaw,
) -> tuple[dict[str, object], ...] | None:
    montage = raw.get_montage()
    if montage is None:
        return None
    ch_pos = montage.get_positions().get("ch_pos") or {}
    if not all(
        name in ch_pos and np.all(np.isfinite(np.asarray(ch_pos[name], dtype=float)))
        for name in raw.ch_names
    ):
        return None
    locations = []
    for index, name in enumerate(raw.ch_names, start=1):
        x_mne, y_mne, z_mne = np.asarray(ch_pos[name], dtype=float)
        azimuth = float(np.degrees(np.arctan2(-x_mne, y_mne)))
        elevation = float(np.degrees(np.arctan2(z_mne, np.hypot(x_mne, y_mne))))
        locations.append(
            {
                "labels": name,
                "X": y_mne,
                "Y": -x_mne,
                "Z": z_mne,
                "sph_theta": azimuth,
                "sph_phi": elevation,
                "sph_radius": float(np.linalg.norm([x_mne, y_mne, z_mne])),
                "theta": -azimuth,
                "radius": 0.5 - elevation / 180.0,
                "urchan": index,
            }
        )
    return tuple(locations)


def _unit_scale(unit: str, data_type: str = "eeg") -> float:
    key = _normalize_unit(unit)
    unit_map = _UNIT_TO_MOLAR if data_type in {"fnirs", "nirs"} else _UNIT_TO_VOLTS
    try:
        return unit_map[key]
    except KeyError as error:
        label = "fNIRS" if data_type in {"fnirs", "nirs"} else "EEG"
        raise ValueError(f"Unsupported {label} unit {unit!r}") from error


def _normalize_unit(unit: str) -> str:
    return unit.strip().lower().replace("µ", "u").replace("μ", "u").replace(" ", "")


def _canonical_unit(unit: str, data_type: str = "eeg") -> str:
    scale = _unit_scale(unit, data_type)
    if data_type in {"fnirs", "nirs"}:
        return {1.0: "M", 1e-3: "mM", 1e-6: "uM", 1e-9: "nM"}[scale]
    return {1.0: "V", 1e-3: "mV", 1e-6: "uV", 1e-9: "nV"}[scale]


def _description(neural: CNDNeural) -> str:
    parts = ["Imported from CND"]
    if neural.device_name:
        parts.append(f"device={neural.device_name}")
    if neural.cnd_version:
        parts.append(f"cndVersion={neural.cnd_version}")
    return "; ".join(parts)


def _handle_unsupported_mne_metadata(
    raws: Sequence[mne.io.BaseRaw], policy: UnsupportedMetadataPolicy
) -> None:
    if policy == "ignore":
        return
    issues: list[str] = []
    for index, raw in enumerate(raws):
        if len(raw.annotations):
            issues.append(f"trial {index}: annotations")
        if raw.info["bads"]:
            issues.append(f"trial {index}: bad-channel list")
        if raw.info["projs"]:
            issues.append(f"trial {index}: projection metadata")
        if raw.first_samp != 0:
            issues.append(f"trial {index}: non-zero first sample")
    if not issues:
        return
    message = (
        "MNE metadata has no standardized CND mapping and will not be exported: "
        + ", ".join(issues)
    )
    if policy == "raise":
        raise CNDUnsupportedError(message)
    warnings.warn(message, RuntimeWarning, stacklevel=3)
