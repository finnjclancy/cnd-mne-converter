"""Exercise the import toolbar in a real MNE Qt viewer and save screenshots."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from importlib.metadata import version
from pathlib import Path

import mne
import numpy as np
from qtpy import QtCore, QtTest, QtWidgets

from cnd_mne import read_cnd_mne
from cnd_mne.gui import add_cnd_import_button


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--neural-unit", required=True)
    parser.add_argument("--subject", default="1")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("docs/results/browser-import")
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    original = read_cnd_mne(
        args.dataset, subject=args.subject, neural_unit=args.neural_unit
    )
    raw = original.raws[0]
    before = raw.get_data().copy()
    # Isolate viewer preferences from the user's normal desktop settings.
    with tempfile.TemporaryDirectory() as settings:
        QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
        QtCore.QSettings.setPath(
            QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, settings
        )
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with mne.viz.use_browser_backend("qt"):
            browser = raw.plot(
                block=False,
                duration=10,
                n_channels=12,
                scalings="auto",
                precompute=False,
            )
        importer = add_cnd_import_button(browser)
        assert add_cnd_import_button(browser) is importer
        browser.resize(1400, 800)
        QtTest.QTest.qWait(500)
        assert browser.grab().save(str(args.output_dir / "mne-open-cnd.png"))
        toolbar = browser.findChild(QtWidgets.QToolBar, "cndImportToolbar")
        toolbar.actions()[0].trigger()
        importer.path.setText(str(args.dataset.resolve()))
        importer.subject.setText(args.subject)
        importer.neural_unit.setCurrentText(args.neural_unit)
        app.processEvents()
        assert importer.window.isVisible()
        assert importer.window.grab().save(str(args.output_dir / "import-dialog.png"))
        errors = []
        importer._show_error = errors.append
        importer._load()
        assert not errors, errors
        imported = importer.last_browser
        imported.resize(1400, 800)
        QtTest.QTest.qWait(500)
        assert imported.isVisible() and not importer.window.isVisible()
        assert imported.mne.inst is importer.recording.raws[0]
        np.testing.assert_array_equal(raw.get_data(), before)
        np.testing.assert_array_equal(imported.mne.inst.get_data(), before)
        assert imported.grab().save(str(args.output_dir / "imported-cnd.png"))
        report = {
            "packages": {
                p: version(p) for p in ("mne", "mne-qt-browser", "PySide6", "qtpy")
            },
            "source_sha256": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(args.dataset.glob("*.mat"))
            },
            "gui_source_sha256": hashlib.sha256(
                (
                    Path(__file__).resolve().parents[1] / "src/cnd_mne/gui.py"
                ).read_bytes()
            ).hexdigest(),
            "unit_argument": args.neural_unit,
            "source_declared_unit": original.cnd.neural.data_unit,
            "unit_note": "Explicit units do not establish physical calibration.",
            "qt_platform": app.platformName(),
            "native_mne_viewer_with_import_button": True,
            "duplicate_installation_reuses_button": True,
            "dialog_opened_by_toolbar_action": True,
            "new_viewer_opened_after_conversion": True,
            "original_viewer_data_unchanged": True,
            "imported_trial_data_exact_match": True,
            "channels": len(imported.mne.inst.ch_names),
            "trials": len(importer.recording.raws),
            "scope": (
                "Opt-in Qt toolbar prototype; "
                "no MNE source patches or upstream integration."
            ),
        }
        (args.output_dir / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
        imported.close()
        browser.close()
        app.processEvents()
    print(args.output_dir)


if __name__ == "__main__":
    main()
