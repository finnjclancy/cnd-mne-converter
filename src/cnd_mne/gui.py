"""Small Qt desktop launcher for opening CND recordings in MNE."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from .mne import MNECNDRecording, MontagePolicy, read_cnd_mne


class CNDImporterApp:
    """A focused CND import window backed by the public converter API."""

    def __init__(self, *, parent: Any = None, open_on_load: bool = False) -> None:
        from qtpy import QtWidgets

        self._qt = QtWidgets
        self.recording: MNECNDRecording | None = None
        self.trial_index = 0
        self.open_on_load = open_on_load

        self.window = (
            QtWidgets.QDialog(parent) if parent is not None else QtWidgets.QWidget()
        )
        self.window.setWindowTitle("CND to MNE")
        self.window.setMinimumSize(680, 350)
        layout = QtWidgets.QGridLayout(self.window)

        layout.addWidget(QtWidgets.QLabel("CND path"), 0, 0)
        self.path = QtWidgets.QLineEdit()
        layout.addWidget(self.path, 0, 1)
        browse = QtWidgets.QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        layout.addWidget(browse, 0, 2)

        layout.addWidget(QtWidgets.QLabel("Subject (optional)"), 1, 0)
        self.subject = QtWidgets.QLineEdit()
        layout.addWidget(self.subject, 1, 1)

        layout.addWidget(QtWidgets.QLabel("Neural unit"), 2, 0)
        self.neural_unit = QtWidgets.QComboBox()
        self.neural_unit.addItems(("", "V", "mV", "uV", "nV"))
        layout.addWidget(self.neural_unit, 2, 1)
        layout.addWidget(
            QtWidgets.QLabel("Leave blank when the CND declares its unit."), 2, 2
        )

        self.use_montage = QtWidgets.QCheckBox("Apply EEGLAB channel coordinates")
        layout.addWidget(self.use_montage, 3, 0, 1, 2)
        scale_layout = QtWidgets.QHBoxLayout()
        scale_layout.addWidget(QtWidgets.QLabel("scale to metres:"))
        self.coordinate_scale = QtWidgets.QLineEdit("0.01")
        self.coordinate_scale.setMaximumWidth(90)
        scale_layout.addWidget(self.coordinate_scale)
        scale_layout.addStretch()
        layout.addLayout(scale_layout, 3, 2)

        controls = QtWidgets.QHBoxLayout()
        open_button = QtWidgets.QPushButton("Open CND")
        open_button.clicked.connect(self._load)
        controls.addWidget(open_button)
        self.previous_button = QtWidgets.QPushButton("Previous trial")
        self.previous_button.clicked.connect(lambda: self._move_trial(-1))
        controls.addWidget(self.previous_button)
        self.next_button = QtWidgets.QPushButton("Next trial")
        self.next_button.clicked.connect(lambda: self._move_trial(1))
        controls.addWidget(self.next_button)
        controls.addStretch()
        layout.addLayout(controls, 4, 0, 1, 3)

        plots = QtWidgets.QHBoxLayout()
        self.viewer_button = QtWidgets.QPushButton("MNE data viewer")
        self.viewer_button.clicked.connect(self._plot_raw)
        plots.addWidget(self.viewer_button)
        self.sensors_button = QtWidgets.QPushButton("Sensor layout")
        self.sensors_button.clicked.connect(self._plot_sensors)
        plots.addWidget(self.sensors_button)
        self.psd_button = QtWidgets.QPushButton("Power spectrum")
        self.psd_button.clicked.connect(self._plot_psd)
        plots.addWidget(self.psd_button)
        plots.addStretch()
        layout.addLayout(plots, 5, 0, 1, 3)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        layout.addWidget(line, 6, 0, 1, 3)
        self.trial = QtWidgets.QLabel("No recording loaded")
        layout.addWidget(self.trial, 7, 0, 1, 3)
        self.status = QtWidgets.QLabel("Choose a CND folder or MATLAB file.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status, 8, 0, 1, 3)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(9, 1)
        self._update_controls()

    def show(self) -> None:
        """Show the import window."""
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def _browse(self) -> None:
        path, _ = self._qt.QFileDialog.getOpenFileName(
            self.window,
            "Choose a CND MATLAB file",
            "",
            "MATLAB files (*.mat);;All files (*)",
        )
        if not path:
            path = self._qt.QFileDialog.getExistingDirectory(
                self.window, "Choose a CND data directory"
            )
        if path:
            self.path.setText(path)

    def _load(self) -> None:
        path = self.path.text().strip()
        if not path:
            self._show_error("Choose a CND path first.")
            return
        try:
            scale = None
            montage: MontagePolicy = "none"
            if self.use_montage.isChecked():
                montage = "eeglab"
                scale = float(self.coordinate_scale.text())
            self.recording = read_cnd_mne(
                Path(path),
                subject=self.subject.text().strip() or None,
                neural_unit=self.neural_unit.currentText().strip() or None,
                montage=montage,
                coordinate_scale_to_meters=scale,
            )
        except Exception as error:
            self.recording = None
            self.status.setText(f"Could not open CND: {error}")
            self._update_controls()
            self._show_error(str(error))
            return
        self.trial_index = 0
        warning = self._amplitude_warning()
        neural = self.recording.cnd.neural
        unit_note = (
            f"Source unit is not declared; using the user-supplied "
            f"{self.recording.neural_unit} assumption."
            if neural is not None and neural.data_unit is None
            else f"Using source-declared unit {self.recording.neural_unit}."
        )
        self.status.setText(
            warning
            or f"Loaded successfully. {unit_note} Use the MNE buttons to inspect it."
        )
        if warning:
            self._qt.QMessageBox.warning(self.window, "Check the neural unit", warning)
        self._update_controls()
        if self.open_on_load:
            try:
                self._open_browser(self._selected_raw())
            except Exception as error:
                self._show_error(str(error))
            else:
                self.window.hide()

    def _amplitude_warning(self) -> str | None:
        """Flag an implausibly large EEG display without guessing a replacement unit."""
        import numpy as np

        raw = self._selected_raw()
        eeg = raw.get_data(picks="eeg")
        if eeg.size and float(np.nanpercentile(np.abs(eeg), 99)) > 0.1:
            return (
                "The EEG amplitude is unusually large for data expressed in volts. "
                "Check the neural unit before interpreting the MNE viewer."
            )
        return None

    def _show_error(self, message: str) -> None:
        self._qt.QMessageBox.critical(self.window, "CND to MNE", message)

    def _selected_raw(self) -> Any:
        if self.recording is None:
            raise RuntimeError("Open a CND recording first")
        return self.recording.raws[self.trial_index]

    def _move_trial(self, amount: int) -> None:
        if self.recording is None:
            return
        self.trial_index = min(
            max(0, self.trial_index + amount), len(self.recording.raws) - 1
        )
        self._update_controls()

    def _plot_raw(self) -> None:
        self._run_plot(self._open_browser)

    def _open_browser(self, raw: Any) -> Any:
        """Open an ordinary MNE Qt viewer with our opt-in import toolbar."""
        import mne

        with mne.viz.use_browser_backend("qt"):
            browser = raw.plot(
                block=False,
                duration=min(10.0, raw.times[-1]),
                n_channels=min(20, len(raw.ch_names)),
                scalings="auto",
            )
        importer = add_cnd_import_button(browser)
        importer.recording = self.recording
        importer.trial_index = self.trial_index
        importer.path.setText(self.path.text())
        importer.subject.setText(self.subject.text())
        importer.neural_unit.setCurrentText(self.neural_unit.currentText())
        importer.use_montage.setChecked(self.use_montage.isChecked())
        importer.coordinate_scale.setText(self.coordinate_scale.text())
        importer.status.setText(self.status.text())
        importer._update_controls()
        # Keep the original CND metadata reachable for later template write-back.
        browser.cnd_recording = self.recording
        browser.cnd_trial_index = self.trial_index
        self.last_browser = browser
        return browser

    def _plot_sensors(self) -> None:
        self._run_plot(self._plot_sensor_layout)

    def _plot_sensor_layout(self, raw: Any) -> None:
        """Use an MNE head transform when the channels exactly match BioSemi."""
        display_raw, montage_name = self._display_raw(raw)
        figure = display_raw.plot_sensors(show_names=True, show=True)
        if montage_name:
            figure.axes[0].set_title(
                f"MNE {montage_name.capitalize()} head layout (matched by channel name)"
            )
            self.status.setText(
                f"Displayed with MNE's {montage_name} head transform; "
                "the original CND coordinates remain unchanged."
            )

    def _plot_psd(self) -> None:
        self._run_plot(self._plot_power_spectrum)

    def _plot_power_spectrum(self, raw: Any) -> None:
        """Plot power using the same display coordinates as the sensor view."""
        display_raw, montage_name = self._display_raw(raw)
        sphere = self._topomap_sphere(display_raw) if montage_name else "auto"
        display_raw.compute_psd().plot(show=True, sphere=sphere)
        if montage_name:
            self.status.setText(
                f"Power topomaps use MNE's {montage_name} head transform; "
                "the original CND coordinates remain unchanged."
            )

    @staticmethod
    def _display_raw(raw: Any) -> tuple[Any, str | None]:
        """Recognise complete BioSemi data already transformed by the converter."""
        import mne

        if raw.get_montage() is None:
            return raw, None
        if "device=biosemi" not in (raw.info["description"] or "").lower():
            return raw, None
        for candidate in (
            "biosemi16",
            "biosemi32",
            "biosemi64",
            "biosemi128",
            "biosemi160",
            "biosemi256",
        ):
            montage = mne.channels.make_standard_montage(candidate, head_size=0.095)
            if set(raw.ch_names) == set(montage.ch_names):
                return raw, candidate
        return raw, None

    @staticmethod
    def _topomap_sphere(raw: Any) -> tuple[float, float, float, float]:
        """Fit a display outline that contains the full projected sensor cap."""
        import mne
        import numpy as np

        radius, origin, _ = mne.bem.fit_sphere_to_headshape(
            raw.info, units="m", verbose=False
        )
        positions = np.asarray(
            list(raw.get_montage().get_positions()["ch_pos"].values())
        )
        relative = positions - origin
        polar_angles = np.arctan2(
            np.linalg.norm(relative[:, :2], axis=1), relative[:, 2]
        )
        projected_radii = 2.0 * radius * polar_angles / np.pi
        display_radius = max(radius, float(projected_radii.max()) * 1.01)
        return float(origin[0]), float(origin[1]), float(origin[2]), display_radius

    def _run_plot(self, operation: Any) -> None:
        try:
            operation(self._selected_raw())
        except Exception as error:
            self._show_error(str(error))

    def _update_controls(self) -> None:
        recording = self.recording
        count = len(recording.raws) if recording is not None else 0
        loaded = count > 0
        self.previous_button.setEnabled(loaded and self.trial_index > 0)
        self.next_button.setEnabled(
            recording is not None and self.trial_index < len(recording.raws) - 1
        )
        for button in (
            self.viewer_button,
            self.sensors_button,
            self.psd_button,
        ):
            button.setEnabled(loaded)
        self.trial.setText(
            f"Trial {self.trial_index + 1} of {count}"
            if loaded
            else "No recording loaded"
        )


def add_cnd_import_button(browser: Any) -> CNDImporterApp:
    """Add an Open CND toolbar action to an existing MNE Qt browser.

    Pass the figure returned by ``raw.plot()`` with the Qt browser backend.
    Only this window is extended; no MNE functions or installed files are
    patched. Importing opens a new viewer, preserving the existing recording.
    Returns the import-dialog controller. Repeated calls reuse the same button.
    This is a prototype using Qt's public window API, not an MNE plugin API.
    """
    from qtpy import QtWidgets

    if not isinstance(browser, QtWidgets.QMainWindow):
        raise TypeError(
            "Open CND requires MNE's Qt browser. Use "
            "mne.viz.set_browser_backend('qt') before raw.plot()."
        )
    existing = getattr(browser, "_cnd_import_controller", None)
    if existing is not None:
        return existing
    importer = CNDImporterApp(parent=browser, open_on_load=True)
    toolbar = QtWidgets.QToolBar("CND import", browser)
    toolbar.setObjectName("cndImportToolbar")
    action = toolbar.addAction("Open CND…")
    action.setObjectName("openCNDAction")
    action.setToolTip("Import a CND MATLAB recording into a new MNE viewer")
    action.triggered.connect(importer.show)
    browser.addToolBar(toolbar)
    cast(Any, browser)._cnd_import_controller = importer
    return importer


def launch_gui() -> None:
    """Launch the CND-to-MNE desktop import window."""
    try:
        from qtpy import QtWidgets
    except ImportError as error:
        raise RuntimeError(
            "The CND GUI requires the optional GUI dependencies. "
            "Install them with `pip install 'cnd-mne-converter[gui]'`."
        ) from error

    application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = CNDImporterApp()
    window.show()
    application.exec()
