"""Generate the small, redistributable CND fixture committed under tests/data."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from cnd_mne import CNDNeural, CNDRecording, CNDStimulus, write_cnd

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "tests" / "data" / "minimal-cnd"


def main() -> None:
    """Write a deterministic two-trial CND 1.0 example."""
    sfreq = 100.0
    lengths = (100, 125)
    neural_trials = tuple(
        np.column_stack(
            [
                10 * np.sin(2 * np.pi * frequency * np.arange(length) / sfreq)
                for frequency in (3, 5, 7, 11)
            ]
        )
        for length in lengths
    )
    envelope = tuple(
        np.linspace(0.0, 1.0, length, dtype=np.float64) for length in lengths
    )
    onsets = []
    for length in lengths:
        values = np.zeros(length, dtype=np.float64)
        values[10::25] = 1.0
        onsets.append(values)

    recording = CNDRecording(
        neural=CNDNeural(
            trials=neural_trials,
            sfreq=sfreq,
            data_type="EEG",
            device_name="Synthetic four-channel system",
            original_trial_positions=(2, 1),
            channel_locations=(
                {"labels": "Fz", "X": 0.0, "Y": 0.5, "Z": 0.8},
                {"labels": "Cz", "X": 0.0, "Y": 0.0, "Z": 1.0},
                {"labels": "Pz", "X": 0.0, "Y": -0.5, "Z": 0.8},
                {"labels": "Oz", "X": 0.0, "Y": -0.8, "Z": 0.5},
            ),
            external_trials=tuple(
                np.zeros((length, 1), dtype=np.float64) for length in lengths
            ),
            external_description="Synthetic EOG",
            cnd_version=1.0,
            data_unit="uV",
            extra_fields={"fixturePurpose": "automated interoperability tests"},
        ),
        stimulus=CNDStimulus(
            names=("Speech Envelope", "Word Onsets"),
            features=(envelope, tuple(onsets)),
            sfreq=sfreq,
            stimulus_indices=(101, 102),
            condition_indices=(1, 2),
            condition_names=("Listening", "Control"),
            cnd_version=1.0,
        ),
    )
    paths = write_cnd(recording, DESTINATION, overwrite=True)
    for path in (paths.neural, paths.stimulus):
        assert path is not None
        _normalize_mat_header(path)


def _normalize_mat_header(path: Path) -> None:
    header = (
        b"MATLAB 5.0 MAT-file, Platform: cnd-mne-converter, "
        b"Created for deterministic tests"
    )
    with path.open("r+b") as handle:
        handle.write(header.ljust(116, b" "))


if __name__ == "__main__":
    main()
