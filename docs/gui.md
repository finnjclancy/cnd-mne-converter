# CND-to-MNE desktop GUI

The GUI opens a CND recording and passes each neural trial to MNE-Python. It is
a companion window supplied by this package, not an upstream MNE or MNELAB
plugin.

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
