"""Conservative adapters between canonical CND data and MNE-Python."""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal

import mne
import numpy as np

from .exceptions import CNDAmbiguousUnitError, CNDUnsupportedError, CNDValidationError
from .model import CNDNeural, CNDRecording, CNDStimulus, CNDTrialMetadata, CNDVersion
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


@dataclass(slots=True)
class MNECNDRecording:
    """MNE trials paired with the complete source CND representation."""

    raws: tuple[mne.io.RawArray, ...]
    cnd: CNDRecording
    neural_unit: str

    @property
    def stimulus(self) -> CNDStimulus | None:
        return self.cnd.stimulus

    @property
    def trial_metadata(self) -> tuple[CNDTrialMetadata, ...]:
        """Return CND trial metadata aligned with :attr:`raws`."""
        return self.cnd.trial_metadata

    @property
    def trial_slices(self) -> tuple[slice, ...]:
        """Return sample slices locating trials in :meth:`concatenate` output."""
        start = 0
        output: list[slice] = []
        for raw in self.raws:
            stop = start + raw.n_times
            output.append(slice(start, stop))
            start = stop
        return tuple(output)

    def concatenate(self, *, add_trial_annotations: bool = True) -> mne.io.BaseRaw:
        """Return an explicit continuous view with protected trial boundaries.

        MNE adds ``BAD boundary`` and ``EDGE boundary`` annotations at every
        artificial join. The source per-trial objects are copied and remain
        unchanged. Optional ``CND_TRIAL/<one-based-index>`` annotations make
        the original trial starts directly visible in MNE.
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
        """Represent one CND stimulus feature set as MNE ``misc`` channels.

        The stimulus sampling rate and numerical values are preserved. No
        resampling, alignment shift, or physical-unit claim is made. A
        multivariate feature such as a spectrogram becomes one ``misc``
        channel per feature dimension.
        """
        stimulus = self.stimulus
        if stimulus is None:
            raise CNDValidationError("CND recording has no stimulus data")
        if isinstance(feature, str):
            try:
                feature_index = stimulus.names.index(feature)
            except ValueError as error:
                raise KeyError(feature) from error
        else:
            feature_index = int(feature)
            if not 0 <= feature_index < stimulus.n_features:
                raise IndexError(feature_index)
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

    def to_cnd(
        self,
        *,
        output_unit: str | None = None,
        on_unsupported_metadata: UnsupportedMetadataPolicy = "warn",
    ) -> CNDRecording:
        """Export edited MNE values while preserving the complete CND template."""
        return from_mne(
            self.raws,
            template=self.cnd,
            output_unit=output_unit or self.neural_unit,
            on_unsupported_metadata=on_unsupported_metadata,
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
        Canonical CND data.
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
    if neural.data_type.strip().lower() != "eeg":
        raise CNDUnsupportedError(
            f"MVP adapter supports EEG only, not {neural.data_type!r}"
        )

    unit = neural_unit or neural.data_unit
    if unit is None:
        raise CNDAmbiguousUnitError(
            "CND does not declare the EEG unit; pass neural_unit='V', 'mV', "
            "'uV', or 'nV' explicitly"
        )
    scale = _unit_scale(unit)
    ch_names = neural.channel_names
    if ch_names is None:
        ch_names = tuple(f"EEG{index:03d}" for index in range(1, neural.n_channels + 1))
        warnings.warn(
            "CND has no complete channel labels; generated EEG001... names "
            "and omitted montage",
            RuntimeWarning,
            stacklevel=2,
        )
        montage = "none"

    if len(set(ch_names)) != len(ch_names):
        raise CNDValidationError("CND channel labels are not unique")
    info = mne.create_info(list(ch_names), neural.sfreq, ch_types="eeg")
    info["description"] = _description(neural)

    dig_montage = _make_montage(
        neural,
        ch_names,
        montage=montage,
        coordinate_scale_to_meters=coordinate_scale_to_meters,
    )
    raws: list[mne.io.RawArray] = []
    for trial in neural.trials:
        data_volts = np.asarray(trial, dtype=np.float64).T * scale
        raw = mne.io.RawArray(data_volts, info.copy(), verbose="ERROR")
        if dig_montage is not None:
            raw.set_montage(dig_montage, on_missing="raise", verbose="ERROR")
        raws.append(raw)
    return MNECNDRecording(tuple(raws), recording, _canonical_unit(unit))


def from_mne(
    raws: mne.io.BaseRaw | Sequence[mne.io.BaseRaw],
    *,
    stimulus: CNDStimulus | None = None,
    output_unit: str = "V",
    device_name: str | None = None,
    original_trial_positions: Sequence[int] | None = None,
    cnd_version: CNDVersion | None = 1.0,
    template: CNDRecording | None = None,
    on_unsupported_metadata: UnsupportedMetadataPolicy = "warn",
) -> CNDRecording:
    """Create canonical CND data from one or more MNE raw recordings.

    MNE stores EEG in volts. ``output_unit`` controls the numerical values
    written to CND and is recorded in the extension field ``dataUnit``.
    Arbitrary stimulus features cannot be inferred from MNE and must be passed
    explicitly when required. Pass ``template`` (or use
    :meth:`MNECNDRecording.to_cnd`) for a controlled round trip that preserves
    CND-only metadata and stimulus features.
    """
    raw_trials = (raws,) if isinstance(raws, mne.io.BaseRaw) else tuple(raws)
    if not raw_trials:
        raise CNDValidationError("At least one MNE Raw object is required")
    if on_unsupported_metadata not in {"warn", "raise", "ignore"}:
        raise ValueError("on_unsupported_metadata must be 'warn', 'raise', or 'ignore'")
    _handle_unsupported_mne_metadata(raw_trials, on_unsupported_metadata)

    first = raw_trials[0]
    sfreq = float(first.info["sfreq"])
    ch_names = tuple(first.ch_names)
    ch_types = tuple(first.get_channel_types())
    if any(channel_type != "eeg" for channel_type in ch_types):
        raise CNDUnsupportedError(
            "MVP exporter requires all selected MNE channels to have type 'eeg'"
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

    template_neural = template.neural if template is not None else None
    if template is not None and template_neural is None:
        raise CNDValidationError("CND template has no neural data")
    if template_neural is not None:
        if len(raw_trials) != template_neural.n_trials:
            raise CNDValidationError("MNE trial count does not match the CND template")
        template_names = template_neural.channel_names or tuple(
            f"EEG{index:03d}" for index in range(1, template_neural.n_channels + 1)
        )
        if ch_names != template_names:
            raise CNDValidationError(
                "MNE channel names/order do not match the CND template"
            )
        for index, (raw, source_trial) in enumerate(
            zip(raw_trials, template_neural.trials, strict=True)
        ):
            if raw.n_times != np.asarray(source_trial).shape[0]:
                raise CNDValidationError(
                    f"MNE trial {index} length does not match the CND template; "
                    "supply synchronized replacement stimulus/external data through "
                    "a new CND recording instead"
                )

    volts_per_output_unit = _unit_scale(output_unit)
    trials = tuple(raw.get_data().T / volts_per_output_unit for raw in raw_trials)
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
        neural = replace(
            template_neural,
            trials=trials,
            sfreq=sfreq,
            device_name=device_name or template_neural.device_name,
            original_trial_positions=original,
            data_unit=_canonical_unit(output_unit),
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
            cnd_version=cnd_version,
            data_unit=_canonical_unit(output_unit),
            extra_fields=extras,
            variable_name="eeg",
        )
        resolved_stimulus = stimulus
    recording = CNDRecording(neural, resolved_stimulus)
    validate_cnd(recording).raise_for_errors()
    return recording


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
    return mne.channels.make_dig_montage(ch_pos=positions, coord_frame="head")


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
        locations.append(
            {
                "labels": name,
                "X": y_mne,
                "Y": -x_mne,
                "Z": z_mne,
                "urchan": index,
            }
        )
    return tuple(locations)


def _unit_scale(unit: str) -> float:
    key = _normalize_unit(unit)
    try:
        return _UNIT_TO_VOLTS[key]
    except KeyError as error:
        raise ValueError(f"Unsupported EEG unit {unit!r}") from error


def _normalize_unit(unit: str) -> str:
    return unit.strip().lower().replace("µ", "u").replace("μ", "u").replace(" ", "")


def _canonical_unit(unit: str) -> str:
    scale = _unit_scale(unit)
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
