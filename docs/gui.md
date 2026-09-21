# CND-to-MNE desktop GUI

The GUI opens a CND recording and passes each neural trial to MNE-Python. It is
a companion window supplied by this package, not an upstream MNE or MNELAB
plugin.

## Import button inside MNE's Qt viewer (prototype)

The package can now add **Open CND…** directly to an MNE Qt browser window.
It opens an import dialog with explicit unit and coordinate-scale controls.
Successful imports open a new normal MNE viewer; the existing recording and its
edits remain in the original viewer. Trials remain separate Raw objects.
Reopen the dialog to select another trial and click **MNE data viewer** to view it.

The companion window adds this toolbar automatically when you click **MNE data
viewer**. To start directly in the viewer using the bundled synthetic example:

```bash
uv sync --locked --extra gui
uv run --extra gui python examples/mne_import_button.py
```

For an existing MNE Raw object, enable the extension explicitly:

```python
import mne
from cnd_mne.gui import add_cnd_import_button

with mne.viz.use_browser_backend("qt"):
    browser = raw.plot(block=False)
importer = add_cnd_import_button(browser)
```

In a plain Python script, keep the Qt event loop running (see the standalone
example). QtPy uses the active Qt binding; the `gui` extra supplies PySide6.
The Matplotlib browser is not supported by this toolbar.

This is an opt-in prototype implemented with Qt's public window/toolbar API.
It does not patch MNE's source, register a global reader, or change unrelated
viewer windows. MNE does not supply this CND button: it is added by our package
to the viewer instance. It is not an official MNE plugin interface or accepted
upstream integration. This is the working example to review with collaborators
before proposing a supported integration to the MNE team.

Viewers opened by our importer retain the CND wrapper on `browser.cnd_recording`
and the selected trial on `browser.cnd_trial_index`; the import button itself
does not automatically save edits or overwrite CND files.

The prototype was tested with MNE 1.12.1, mne-qt-browser 0.7.5 and PySide6
6.11.2. The real Lalor sample (128 channels, 20 trials) passed import from the
toolbar, with exact trial-data equality and the original viewer's data unchanged.
[Screenshots and the numerical audit](results/browser-import/) are included.
These screenshots and checks used offscreen Qt; the automated tests also cover
cancelled/failed imports, repeated button installation and variable-length trials.
The three browser-import tests also passed against the built wheel in a fresh
Python 3.13 environment with MNE 1.13.2 and mne-qt-browser 0.7.5.
Reproduce the real-data check after downloading the walkthrough's Lalor fixture:

```bash
QT_QPA_PLATFORM=offscreen MNE_BROWSER_PRECOMPUTE=false \
  uv run --extra gui python examples/validate_browser_import.py \
  examples/_scratch/lalor-sample --neural-unit uV
```

The unit argument here is the existing demonstration assumption, not a verified
source calibration. Run `uv run --extra dev --extra gui pytest
tests/test_browser_import.py` for the bundled-fixture tests.

## Install and launch

From the repository root:

```bash
uv sync --extra gui
uv run cnd-mne gui
```

## Inputs

- **CND path:** a CND dataset directory or a neural MATLAB file. When opening a
  neural file directly, the corresponding `dataStim.mat` should be beside it.
- **Subject:** selects one participant when a directory contains multiple
  subject files. It can remain blank for a single-subject directory.
- **Neural unit:** the unit of the numerical EEG samples. Leave it blank only
  when the CND file declares a unit. MNE stores EEG internally in volts, so a
  wrong selection changes the displayed amplitude. The GUI warns when the
  resulting values are unusually large, but it does not guess a replacement.
- **Apply EEGLAB channel coordinates:** converts the CND/EEGLAB channel-location
  fields into an MNE montage.
- **Scale to metres:** multiplier from the stored coordinate values to metres.
  This must come from the dataset documentation; it cannot be inferred safely.

Click **Open CND** after setting these fields. The status line reports an error,
a unit warning, or the number of the selected trial.

## Buttons

- **Previous trial / Next trial:** select one variable-length CND trial. Each
  trial is a separate MNE `Raw` object.
- **MNE data viewer:** opens MNE's interactive signal browser with a readable
  ten-second, twenty-channel initial view. The underlying data are unchanged.
- **Sensor layout:** plots the channel names and positions. When the complete
  channel-name set exactly matches a standard BioSemi 16, 32, 64, 128, 160, or 256
  montage and the CND declares a BioSemi device, the converter applies MNE's
  corresponding native-to-head transform and fiducials while preserving the
  CND electrode directions. The original CND structure remains attached and
  unchanged.
- **Power spectrum:** plots power against frequency. Drag across a frequency
  range to display an MNE scalp topography for that band. The colours show
  interpolated sensor power, not brain anatomy or source-localised activity.
  Recognised BioSemi data use the same display transform as **Sensor layout**.
  The topography fits its schematic outline around the full projected montage.
  Without this display adjustment, MNE retains a conventional head circle but
  expands the interpolation area for BioSemi electrodes below the ear/nasion
  plane, which can make valid lower-cap positions look as though they are
  outside the head.

## Real Lalor Natural Speech example

Use the locally downloaded sample with:

| Field | Value |
| --- | --- |
| CND path | `examples/_scratch/lalor-sample` |
| Subject | blank |
| Neural unit | `uV` |
| Apply EEGLAB channel coordinates | selected |
| Scale to metres | `0.095` |

This recording contains 128 BioSemi channels and 20 variable-length trials.
The `uV` setting is a documented plotting assumption because the source file
does not declare its physical unit.

## Coordinate limits

The Lalor CND coordinate directions agree with the BioSemi factory layout to
within `0.000349°` in the repository validation. For the GUI, the converter
preserves those CND directions and applies the native-to-head transform from
MNE's BioSemi fiducials; the maximum numerical directional change in the audit
is below `0.00004°`. The power topography enlarges its schematic outline to
contain the full projected cap; this affects only the plot, not the coordinates
or EEG values. These are manufacturer template positions rather than digitised
locations measured from the individual participant, so they should not be
treated as subject-specific anatomy.

The reproducible audit is in
[`examples/validate_gui.py`](../examples/validate_gui.py), with its latest JSON
output in
[`docs/results/giovanni-review/gui-audit.json`](results/giovanni-review/gui-audit.json).
