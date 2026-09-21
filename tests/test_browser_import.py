"""Exercise our button in the real optional MNE Qt browser."""

from __future__ import annotations

import os
from pathlib import Path

import mne
import numpy as np
import pytest

from cnd_mne import write_cnd
from cnd_mne.gui import add_cnd_import_button

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("mne_qt_browser")
QtWidgets = pytest.importorskip("qtpy.QtWidgets")
QtCore = pytest.importorskip("qtpy.QtCore")


@pytest.fixture
def qt_app(tmp_path, monkeypatch):
    monkeypatch.setenv("MNE_BROWSER_PRECOMPUTE", "false")
    previous_format = QtCore.QSettings.defaultFormat()
    QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
    QtCore.QSettings.setPath(
        QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, str(tmp_path)
    )
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app
    for window in app.topLevelWidgets():
        window.close()
    app.processEvents()
    QtCore.QSettings.setDefaultFormat(previous_format)


def _browser():
    raw = mne.io.RawArray(
        np.zeros((2, 200)), mne.create_info(["Cz", "Pz"], 100, "eeg"), verbose=False
    )
    with mne.viz.use_browser_backend("qt"):
        browser = raw.plot(show=False, block=False, precompute=False)
    return raw, browser


def test_button_imports_into_real_mne_and_preserves_original(
    qt_app, tmp_path, sample_recording, monkeypatch
):
    paths = write_cnd(sample_recording, tmp_path / "cnd", subject=1)
    original, browser = _browser()
    before = original.get_data().copy()
    importer = add_cnd_import_button(browser)
    assert add_cnd_import_button(browser) is importer
    toolbars = browser.findChildren(QtWidgets.QToolBar, "cndImportToolbar")
    assert len(toolbars) == 1
    toolbars[0].actions()[0].trigger()
    qt_app.processEvents()
    assert importer.window.isVisible()
    errors = []
    monkeypatch.setattr(importer, "_show_error", errors.append)
    importer.path.setText(str(paths.neural))
    importer._load()
    qt_app.processEvents()
    assert not errors
    assert not importer.window.isVisible()
    imported_browser = importer.last_browser
    assert imported_browser is not browser
    assert imported_browser.isVisible()
    assert imported_browser.mne.inst is importer.recording.raws[0]
    np.testing.assert_allclose(
        imported_browser.mne.inst.get_data(), sample_recording.neural.trials[0].T * 1e-6
    )
    np.testing.assert_array_equal(original.get_data(), before)
    assert imported_browser.cnd_recording is importer.recording
    assert len(imported_browser.cnd_recording.raws) == 2
    assert imported_browser.cnd_recording.cnd.neural.extra_fields["customField"] == (
        "preserve me"
    )
    assert imported_browser.findChild(QtWidgets.QToolBar, "cndImportToolbar")
    # Variable-length trials remain separate, and the new viewer can open trial 2.
    next_importer = add_cnd_import_button(imported_browser)
    next_importer._move_trial(1)
    next_importer._plot_raw()
    assert next_importer.last_browser.cnd_trial_index == 1
    assert next_importer.last_browser.mne.inst.n_times == 120


def test_cancel_and_bad_path_leave_existing_viewer_unchanged(qt_app, monkeypatch):
    raw, browser = _browser()
    before = raw.get_data().copy()
    importer = add_cnd_import_button(browser)
    importer.show()
    importer.window.reject()
    assert not hasattr(importer, "last_browser")
    errors = []
    monkeypatch.setattr(importer, "_show_error", errors.append)
    importer.path.setText(str(Path("/missing-cnd-file.mat")))
    importer._load()
    assert errors
    assert not hasattr(importer, "last_browser")
    np.testing.assert_array_equal(raw.get_data(), before)
    assert browser.mne.inst is raw


def test_button_rejects_non_qt_viewer(qt_app):
    with pytest.raises(TypeError, match="Qt browser"):
        add_cnd_import_button(object())
