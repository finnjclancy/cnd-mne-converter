# CND-MNE

A Python package for opening lab brain recordings in Python, analysing them with MNE, and saving them back to the lab's MATLAB format without losing the extra experiment information.

[![CI](https://github.com/finnjclancy/cnd-mne-converter/actions/workflows/ci.yml/badge.svg)](https://github.com/finnjclancy/cnd-mne-converter/actions/workflows/ci.yml)

This repo is public. It is not on PyPI yet.

The [Di Liberto lab](https://www.diliberg.net/) stores experiments as **CND**: MATLAB `.mat` files with the brain signal *and* what the person was hearing or doing at the same time. Public CND is on the [CNSP dataset catalogue](https://cnsp-resources.readthedocs.io/en/latest/datasetsPage.html) ([CND 1.0 spec](https://data.cnspworkshop.net/CND_Specifications.pdf)).

MNE wants one continuous recording (`Raw`) or equal-length snippets (`Epochs`). CND trials can be different lengths, and a speech envelope is not an EEG channel. This package reads the MATLAB, gives you one MNE `Raw` per trial, keeps the leftover CND on `rec.cnd`, and can write it back. It will not invent units, resample, or glue trials together unless you ask.

EEG and the public-catalogue fNIRS layout work. MEG, TRF result files, automatic unit detection, and automatic electrode-coordinate scaling do not.

I ran the verifier on every downloadable collection from that catalogue: 1,026 neural files, 17,774 trials. 1,017 pass. Eight BabyRhythm files convert but contain no neural samples. One SparrKULee1 file (`dataSub48.mat`) is truncated in the published archive. The dummy unit used in those checks is only “multiply by one”; it is not a claim that the files are in volts. [Results](docs/results/README.md).

## Install

You need [git](https://git-scm.com/), [uv](https://docs.astral.sh/uv/), and Python 3.10 or newer.

```bash
git clone https://github.com/finnjclancy/cnd-mne-converter.git
cd cnd-mne-converter
uv sync --extra dev
uv run cnd-mne inspect tests/data/minimal-cnd --subject 1
```

You should see JSON for two trials, four EEG channels, and two stimulus tracks (`Speech Envelope`, `Word Onsets`). `inspect` only reads the MATLAB; it does not need a unit.

### Desktop import button

Launch the companion CND-to-MNE window:

```bash
uv sync --extra gui
uv run cnd-mne gui
```

Choose a CND MATLAB file, provide the neural unit when the file does not declare
one, and click **Open CND**. The window can move between trials and open the
selected trial in MNE's interactive data viewer, sensor-layout plot, or power
spectrum. Applying EEGLAB channel coordinates remains explicit because the
stored coordinate scale cannot safely be guessed.

The MNE Qt viewer opened from this window also includes an **Open CND…** toolbar
button. The opt-in `cnd_mne.gui.add_cnd_import_button(browser)` extension can add
it to an existing Qt viewer. A direct-viewer demonstration is available with
`uv run --extra gui python examples/mne_import_button.py`.

The toolbar is a prototype supplied by this package using Qt's window API;
it does not patch MNE or add the button globally. Direct inclusion in MNE-Python
or a third-party MNE application such as MNELAB remains a separate upstream change.

See the [GUI guide](docs/gui.md) for the fields, buttons, real-data example,
plot interpretation, and coordinate limitations.

## Usage

The bundled example already declares `uV`:

```python
from cnd_mne import read_cnd_mne

rec = read_cnd_mne("tests/data/minimal-cnd", subject=1)
rec.raws[0].plot()
```

`rec.raws` is one MNE `Raw` per trial. `rec.cnd` is the original CND information.

Most public CND files do **not** declare a unit. Then you must pass one the data owner actually confirmed:

```python
rec = read_cnd_mne("/path/to/dataCND", subject=1, neural_unit="uV")
```

If a subject file has more than one recording type:

```python
from cnd_mne import available_neural_variables

print(available_neural_variables("/path/to/dataSub1.mat"))
rec = read_cnd_mne("/path/to/dataSub1.mat", neural_variable="eeg", neural_unit="uV")
```

The unused type stays on `rec.cnd.additional_variables` and is written back on export.

```python
envelope = rec.stimulus_raws("Speech Envelope")
words = rec.stimulus_annotations("Word Onsets")
eog = rec.external_raws(unit="uV", channel_types="eog")
continuous = rec.concatenate()  # opt-in; fake joins are marked
```

For MNE-to-CND conversion, keep reviewed auxiliary channels separate from the
EEG matrix. Their names and MNE channel types are stored with `extChan` and are
restored automatically:

```python
recording = from_mne(
    eeg_raw,
    stimulus=stimulus,
    external_raws=eog_raw,
    external_unit="V",
    external_description="EOG channels",
)
```

Write back through the original template so envelopes and trial order survive:

```python
rec.raws[0].filter(1, 15)
paths = rec.write_cnd(
    "converted/dataCND", subject=1, output_unit="uV", mat_version="7.3"
)
```

For CNSP scripts that access `eeg.extChan{1}`, pass
`cnsp_external_cells=True` to `rec.write_cnd(...)` when re-exporting a legacy
single-group external-channel struct. The default preserves the template layout;
new `external_raws` exports already use cells.

Existing files are left alone unless you pass `overwrite=True`. MNE cannot invent speech envelopes. For data that never was CND, `from_mne(...)` builds a new recording and tells you what it could not represent.

```bash
uv run cnd-mne verify-dataset /path/to/dataset \
  --neural-unit uV \
  --output verification.json
```

`--serialized-round-trip` also writes and rereads MATLAB. `--strict-spec` is for new CND you created, not for messy legacy files. Only pass a unit the owner confirmed.

Notebook: [examples/walkthrough.ipynb](examples/walkthrough.ipynb). Part 1 uses the bundled example. Part 2 downloads the CNSP Lalor Natural Speech sample (~120 MB).

```bash
uv run jupyter notebook examples/walkthrough.ipynb
```

## Repo

```text
src/cnd_mne/      read MATLAB, hold a recording, talk to MNE, write MATLAB
tests/            unit tests plus a tiny fake CND folder for CI
docs/results/     verify-dataset JSON from the public collections
docs/manifests/   checksums of the zips I downloaded
docs/             field mapping
```

The EEG itself is not in git. A clone is under a megabyte.

[Field mapping](docs/field-mapping.md) · [verification results](docs/results/README.md)

```bash
uv run pytest --cov=cnd_mne
uv run ruff check .
uv run ruff format --check .
uv run mypy src/cnd_mne
```

### Validation following Giovanni's review

New MNE external-channel exports use MATLAB cell groups compatible with CNSP's
`eeg.extChan{1}` access. One-dimensional stimulus features are serialized as
`time × 1` columns, rather than MATLAB row vectors.

A labelled BioSemi manufacturer comparison and real ERP CORE MNE filtering/PSD
figures are in [the review results](docs/results/giovanni-review/).
Reproduce from this repository with `uv run --with xlrd python
examples/validate_giovanni.py --root ..`, using the real fixtures and BioSemi
coordinate workbook described in the companion project's
`docs/reports/GIOVANNI-FEEDBACK.md`. The reference head radius is a display
convention, not a measured physical scale.
