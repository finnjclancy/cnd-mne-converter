"""Canonical in-memory representation of a CND recording."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.generic]
CNDVersion = str | int | float


@dataclass(slots=True)
class CNDNeural:
    """Subject-specific neural trials and acquisition metadata.

    Data remain in their original CND numerical unit. Each trial has CND's
    native ``time x channels`` orientation.
    """

    trials: tuple[Array, ...]
    sfreq: float
    data_type: str = "EEG"
    device_name: str | None = None
    original_trial_positions: tuple[int, ...] | None = None
    channel_locations: tuple[dict[str, Any], ...] | None = None
    external_trials: tuple[Array, ...] | None = None
    external_description: str | None = None
    external_fields: dict[str, Any] = field(default_factory=dict)
    rereference: Any = None
    padding_start_sample: Any = None
    cnd_version: CNDVersion | None = None
    data_unit: str | None = None
    signal_types: tuple[str, ...] | None = None
    channels_per_signal_type: tuple[int, ...] | None = None
    extra_fields: dict[str, Any] = field(default_factory=dict)
    variable_name: str = "eeg"
    source_path: Path | None = None

    @property
    def n_trials(self) -> int:
        return len(self.trials)

    @property
    def n_channels(self) -> int:
        if not self.trials:
            return 0
        trial = np.asarray(self.trials[0])
        return int(trial.shape[1]) if trial.ndim == 2 else 0

    @property
    def channel_names(self) -> tuple[str, ...] | None:
        if self.channel_locations is None:
            return None
        names = tuple(
            str(location.get("labels", "")) for location in self.channel_locations
        )
        return names if all(names) else None


@dataclass(slots=True)
class CNDStimulus:
    """Shared continuous stimulus features.

    ``features`` is indexed as ``feature -> trial -> ndarray``. Stimulus data
    keep their own sampling frequency; they are not automatically resampled to
    the neural sampling frequency.
    """

    names: tuple[str, ...]
    features: tuple[tuple[Array, ...], ...]
    sfreq: float
    stimulus_indices: tuple[Any, ...] | None = None
    condition_indices: tuple[Any, ...] | None = None
    condition_names: tuple[str, ...] | None = None
    cnd_version: CNDVersion | None = None
    extra_fields: dict[str, Any] = field(default_factory=dict)
    source_path: Path | None = None

    @property
    def n_features(self) -> int:
        return len(self.features)

    @property
    def n_trials(self) -> int:
        if self.features:
            return len(self.features[0])
        return len(self.stimulus_indices or ())

    @property
    def resolved_stimulus_indices(self) -> tuple[Any, ...]:
        """Return stored indices, or ordinal one-based indices when absent."""
        if self.stimulus_indices is not None:
            return self.stimulus_indices
        return tuple(range(1, self.n_trials + 1))

    def feature(self, name: str) -> tuple[Array, ...]:
        """Return all trials for a named feature."""
        try:
            index = self.names.index(name)
        except ValueError as error:
            raise KeyError(name) from error
        return self.features[index]


@dataclass(slots=True)
class CNDRecording:
    """Canonical CND object retained alongside any MNE representation."""

    neural: CNDNeural | None = None
    stimulus: CNDStimulus | None = None

    @property
    def n_trials(self) -> int:
        if self.neural is not None:
            return self.neural.n_trials
        if self.stimulus is not None:
            return self.stimulus.n_trials
        return 0

    @property
    def trial_metadata(self) -> tuple[CNDTrialMetadata, ...]:
        """Return a normalized, read-only summary for every paired trial."""
        neural = self.neural
        stimulus = self.stimulus
        output: list[CNDTrialMetadata] = []
        for index in range(self.n_trials):
            stimulus_index = None
            condition_index = None
            condition_name = None
            stimulus_samples = None
            stimulus_duration = None
            if stimulus is not None and index < stimulus.n_trials:
                stimulus_index = stimulus.resolved_stimulus_indices[index]
                if stimulus.condition_indices is not None:
                    condition_index = stimulus.condition_indices[index]
                    condition_name = _resolve_condition_name(stimulus, condition_index)
                if stimulus.features:
                    stimulus_samples = int(
                        np.asarray(stimulus.features[0][index]).shape[0]
                    )
                    stimulus_duration = stimulus_samples / stimulus.sfreq

            neural_samples = None
            neural_duration = None
            original_position = None
            if neural is not None and index < neural.n_trials:
                neural_samples = int(np.asarray(neural.trials[index]).shape[0])
                neural_duration = neural_samples / neural.sfreq
                if neural.original_trial_positions is not None:
                    original_position = neural.original_trial_positions[index]

            output.append(
                CNDTrialMetadata(
                    index=index,
                    cnd_index=index + 1,
                    stimulus_index=stimulus_index,
                    condition_index=condition_index,
                    condition_name=condition_name,
                    original_position=original_position,
                    neural_samples=neural_samples,
                    neural_duration_seconds=neural_duration,
                    stimulus_samples=stimulus_samples,
                    stimulus_duration_seconds=stimulus_duration,
                )
            )
        return tuple(output)


@dataclass(slots=True, frozen=True)
class CNDTrialMetadata:
    """Normalized metadata for one zero-indexed Python / one-indexed CND trial."""

    index: int
    cnd_index: int
    stimulus_index: Any = None
    condition_index: Any = None
    condition_name: str | None = None
    original_position: int | None = None
    neural_samples: int | None = None
    neural_duration_seconds: float | None = None
    stimulus_samples: int | None = None
    stimulus_duration_seconds: float | None = None


@dataclass(slots=True, frozen=True)
class CNDPaths:
    """Paths created by :func:`cnd_mne.write_cnd`."""

    neural: Path | None
    stimulus: Path | None


def _resolve_condition_name(stimulus: CNDStimulus, condition_index: Any) -> str | None:
    if isinstance(condition_index, (str, np.str_)):
        return str(condition_index)
    if stimulus.condition_names is None:
        return None
    if isinstance(condition_index, (int, np.integer)):
        offset = int(condition_index) - 1
    elif (
        isinstance(condition_index, (float, np.floating))
        and float(condition_index).is_integer()
    ):
        offset = int(condition_index) - 1
    else:
        return None
    if 0 <= offset < len(stimulus.condition_names):
        return stimulus.condition_names[offset]
    return None
