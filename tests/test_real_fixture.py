from __future__ import annotations

from pathlib import Path

import mne
import numpy as np

from cnd_mne import read_cnd, to_mne

FIXTURE = Path(__file__).parent / "data" / "minimal-cnd"


def test_committed_matlab_fixture_loads_and_converts() -> None:
    recording = read_cnd(FIXTURE, subject=1)

    assert recording.neural.n_trials == 2
    assert recording.neural.n_channels == 4
    assert recording.neural.cnd_version == 1.0
    assert recording.stimulus.names == ("Speech Envelope", "Word Onsets")

    converted = to_mne(recording)
    assert converted.raws[0].ch_names == ["Fz", "Cz", "Pz", "Oz"]
    assert converted.raws[0].get_data().shape == (4, 100)


def test_mne_fif_interoperability(tmp_path) -> None:
    recording = read_cnd(FIXTURE, subject=1)
    raw = to_mne(recording).raws[0]
    fif_path = tmp_path / "fixture_raw.fif"

    raw.save(fif_path, overwrite=True, verbose="ERROR")
    reloaded = mne.io.read_raw_fif(fif_path, preload=True, verbose="ERROR")

    assert reloaded.ch_names == raw.ch_names
    assert reloaded.info["sfreq"] == raw.info["sfreq"]
    np.testing.assert_allclose(reloaded.get_data(), raw.get_data(), atol=1e-12)
