from __future__ import annotations

from unittest.mock import Mock

import mne
import numpy as np

from cnd_mne import cli
from cnd_mne.gui import CNDImporterApp


def test_gui_command_launches_window(monkeypatch) -> None:
    launch = Mock()
    monkeypatch.setattr("cnd_mne.gui.launch_gui", launch)

    assert cli.main(["gui"]) == 0
    launch.assert_called_once_with()


def _raw_with_montage(name: str, *, drop_last: bool = False) -> mne.io.RawArray:
    montage = mne.channels.make_standard_montage(name, head_size=0.095)
    names = montage.ch_names[:-1] if drop_last else montage.ch_names
    data = np.arange(len(names) * 20, dtype=float).reshape(len(names), 20) * 1e-9
    raw = mne.io.RawArray(data, mne.create_info(names, 100, "eeg"), verbose=False)
    raw.set_montage(montage)
    raw.info["description"] = "Imported from CND; device=BioSemi"
    return raw


def test_display_raw_uses_exact_biosemi_template_without_changing_data() -> None:
    raw = _raw_with_montage("biosemi128")
    expected = raw.get_data().copy()

    display, montage_name = CNDImporterApp._display_raw(raw)

    assert montage_name == "biosemi128"
    assert display is raw
    np.testing.assert_array_equal(display.get_data(), expected)
    np.testing.assert_array_equal(raw.get_data(), expected)
    assert display.get_montage().get_positions()["coord_frame"] == "head"


def test_display_raw_does_not_guess_from_incomplete_channel_set() -> None:
    raw = _raw_with_montage("biosemi128", drop_last=True)

    display, montage_name = CNDImporterApp._display_raw(raw)

    assert display is raw
    assert montage_name is None


def test_topomap_sphere_contains_complete_biosemi_projection() -> None:
    from mne.viz.topomap import _prepare_topomap_plot

    raw = _raw_with_montage("biosemi128")
    sphere = CNDImporterApp._topomap_sphere(raw)
    positions = _prepare_topomap_plot(raw.info, "eeg", sphere=sphere)[1]

    assert np.linalg.norm(positions, axis=1).max() <= sphere[3]
