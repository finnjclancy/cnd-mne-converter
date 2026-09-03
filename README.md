# CND-MNE

A Python package for opening lab brain recordings in Python, analysing them with MNE, and saving them back to the lab's MATLAB format without losing the extra experiment information.

[![CI](https://github.com/finnjclancy/cnd-mne-converter/actions/workflows/ci.yml/badge.svg)](https://github.com/finnjclancy/cnd-mne-converter/actions/workflows/ci.yml)

This GitHub repo is private. You need collaborator access before `git clone` will work. It is not on PyPI yet.

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

Write back through the original template so envelopes and trial order survive:

```python
rec.raws[0].filter(1, 15)
paths = rec.write_cnd(
    "converted/dataCND", subject=1, output_unit="uV", mat_version="7.3"
)
```

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
