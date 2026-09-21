"""Open an MNE Qt viewer with the optional CND import toolbar prototype."""

from __future__ import annotations

import argparse
from pathlib import Path

import mne
from qtpy import QtWidgets

from cnd_mne import read_cnd_mne
from cnd_mne.gui import add_cnd_import_button


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=Path(__file__).resolve().parents[1] / "tests/data/minimal-cnd",
        help="Initial CND recording; defaults to the bundled synthetic example",
    )
    parser.add_argument("--subject", default="1")
    parser.add_argument("--neural-unit")
    parser.add_argument("--coordinate-scale", type=float)
    args = parser.parse_args()
    recording = read_cnd_mne(
        args.path,
        subject=args.subject,
        neural_unit=args.neural_unit,
        montage="eeglab" if args.coordinate_scale is not None else "none",
        coordinate_scale_to_meters=args.coordinate_scale,
    )
    application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    raw = recording.raws[0]
    with mne.viz.use_browser_backend("qt"):
        browser = raw.plot(
            block=False,
            duration=min(10.0, raw.times[-1]),
            n_channels=min(20, len(raw.ch_names)),
            scalings="auto",
        )
    importer = add_cnd_import_button(browser)
    importer.recording = recording
    importer.path.setText(str(args.path.resolve()))
    importer.subject.setText(args.subject)
    importer.neural_unit.setCurrentText(args.neural_unit or "")
    if args.coordinate_scale is not None:
        importer.use_montage.setChecked(True)
        importer.coordinate_scale.setText(str(args.coordinate_scale))
    importer._update_controls()
    browser.cnd_recording = recording
    browser.cnd_trial_index = 0
    application.exec()


if __name__ == "__main__":
    main()
