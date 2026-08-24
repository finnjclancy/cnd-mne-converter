from __future__ import annotations

import numpy as np
import pytest

from cnd_mne import CNDNeural, CNDRecording, CNDStimulus


@pytest.fixture
def sample_recording() -> CNDRecording:
    neural = CNDNeural(
        trials=(
            np.arange(200, dtype=float).reshape(100, 2),
            np.arange(240, dtype=float).reshape(120, 2),
        ),
        sfreq=100.0,
        data_type="EEG",
        device_name="Synthetic",
        original_trial_positions=(2, 1),
        channel_locations=(
            {"labels": "Cz", "X": 0.0, "Y": 0.0, "Z": 1.0, "urchan": 1},
            {"labels": "Pz", "X": 0.0, "Y": -0.5, "Z": 0.8, "urchan": 2},
        ),
        external_trials=(
            np.ones((100, 2)),
            np.ones((120, 2)) * 2,
        ),
        external_description="Mastoids",
        external_fields={"channelType": "mastoids"},
        cnd_version=1.0,
        data_unit="uV",
        extra_fields={"customField": "preserve me"},
    )
    stimulus = CNDStimulus(
        names=("Envelope", "Word Onsets"),
        features=(
            (np.linspace(0, 1, 10), np.linspace(0, 1, 12)),
            (np.eye(1, 10, 2).ravel(), np.eye(1, 12, 3).ravel()),
        ),
        sfreq=10.0,
        stimulus_indices=(1, 2),
        condition_indices=(1, 2),
        condition_names=("A", "B"),
        cnd_version=1.0,
        extra_fields={"customStimField": 42},
    )
    return CNDRecording(neural, stimulus)
