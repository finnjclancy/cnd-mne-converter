"""Human- and machine-readable summaries of CND recordings."""

from __future__ import annotations

from typing import Any

import numpy as np

from .model import CNDRecording
from .validation import validate_cnd


def inspect_cnd(
    recording: CNDRecording, *, strict_spec: bool = False
) -> dict[str, Any]:
    """Return a JSON-serializable structural and validation summary."""
    neural = recording.neural
    stimulus = recording.stimulus
    report = validate_cnd(recording, strict_spec=strict_spec)
    output: dict[str, Any] = {
        "n_trials": recording.n_trials,
        "strict_spec": strict_spec,
        "neural": None,
        "stimulus": None,
        "validation": {
            "is_valid": report.is_valid,
            "errors": [
                {"code": issue.code, "path": issue.path, "message": issue.message}
                for issue in report.errors
            ],
            "warnings": [
                {"code": issue.code, "path": issue.path, "message": issue.message}
                for issue in report.warnings
            ],
        },
    }
    if neural is not None:
        output["neural"] = {
            "source": str(neural.source_path) if neural.source_path else None,
            "variable_name": neural.variable_name,
            "data_type": neural.data_type,
            "device_name": neural.device_name,
            "sfreq": neural.sfreq,
            "data_unit": neural.data_unit,
            "n_trials": neural.n_trials,
            "n_channels": neural.n_channels,
            "trial_shapes": [list(np.asarray(trial).shape) for trial in neural.trials],
            "has_channel_locations": neural.channel_locations is not None,
            "has_external_channels": neural.external_trials is not None,
            "has_padding_start_sample": neural.padding_start_sample is not None,
            "cnd_version": neural.cnd_version,
            "extra_fields": sorted(neural.extra_fields),
        }
    if stimulus is not None:
        output["stimulus"] = {
            "source": str(stimulus.source_path) if stimulus.source_path else None,
            "sfreq": stimulus.sfreq,
            "n_trials": stimulus.n_trials,
            "n_features": stimulus.n_features,
            "feature_names": list(stimulus.names),
            "feature_shapes": [
                [list(np.asarray(trial).shape) for trial in feature]
                for feature in stimulus.features
            ],
            "condition_names": (
                list(stimulus.condition_names)
                if stimulus.condition_names is not None
                else None
            ),
            "cnd_version": stimulus.cnd_version,
            "extra_fields": sorted(stimulus.extra_fields),
        }
    return output
