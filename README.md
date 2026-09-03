# CND-MNE

A Python package for opening lab brain recordings in Python, analysing them with MNE, and saving them back to the lab's MATLAB format without losing the extra experiment information.

[![CI](https://github.com/finnjclancy/cnd-mne-converter/actions/workflows/ci.yml/badge.svg)](https://github.com/finnjclancy/cnd-mne-converter/actions/workflows/ci.yml)

This GitHub repo is private. You need collaborator access before `git clone` will work. It is not on PyPI yet.

## Why this exists

The [Di Liberto lab](https://www.diliberg.net/) stores experiments as **CND** (Continuous-event Neural Data): MATLAB `.mat` files with the brain signal *and* what the person was hearing or doing at the same time. Public CND recordings are listed on the [CNSP dataset catalogue](https://cnsp-resources.readthedocs.io/en/latest/datasetsPage.html). The format is the [CND 1.0 spec](https://data.cnspworkshop.net/CND_Specifications.pdf).

Python's usual EEG library is **MNE**. MNE is built around one continuous recording (`Raw`) or equal-length snippets (`Epochs`). CND is messier: trials can be different lengths, and the speech envelope is not an EEG channel. If you force CND into one `Raw`, you lose that extra data.

This package is the bridge. You can plot and filter in MNE, then write the result back to CND. It will not invent units, resample, or glue trials together unless you ask.

## Words used here

- **EEG** — electrical activity recorded from the scalp.
- **fNIRS** — a related optical brain measure. The [public catalogue](https://cnsp-resources.readthedocs.io/en/latest/datasetsPage.html) has one of these layouts; this package can load it.
- **Trial** — one chunk of an experiment. In CND these can be different lengths.
- **Stimulus file** — `dataStim.mat`: speech envelopes, word onsets, condition labels, and similar tracks, lined up with the trials.
- **Neural file** — `dataSubN.mat`: the brain signal for subject N.
- **MNE** — the Python library most people use for EEG. This package talks to it; it is not MNE itself.
- **MATLAB v5 / v7.3** — two `.mat` file versions. v7.3 is HDF5 underneath. Both are supported.

## What you get

- Read and write CND neural + stimulus files
- One MNE `Raw` per trial (because trials are often different lengths)
- The leftover CND fields kept on a companion object, so a round trip does not drop them
- Optional views of stimulus tracks, sparse events, and extra sensors (mastoids, EOG, …)
- Optional concatenation, with markers where trials were glued together
- Command-line `inspect` and `verify-dataset`

EEG and the fNIRS layout in the [public catalogue](https://cnsp-resources.readthedocs.io/en/latest/datasetsPage.html) work. MEG (a different scanner that records magnetic fields), TRF result files (a later analysis, not the raw recording), automatic unit detection, and automatic electrode-coordinate scaling do not.

I ran the verifier on every downloadable collection linked from that catalogue: 1,026 neural files, 17,774 trials. 1,017 pass. Eight BabyRhythm files convert but contain no neural samples. One file in the SparrKULee1 zip (`dataSub48.mat`) is truncated in the published archive. Details: [docs/results](docs/results/README.md).

Those numerical checks can use a dummy unit of 1 when the file has no unit. That only tests whether values were copied or flipped. It does not mean the files are in volts.

## Download and install

You need [git](https://git-scm.com/), [uv](https://docs.astral.sh/uv/), and Python 3.10 or newer.

```bash
git clone https://github.com/finnjclancy/cnd-mne-converter.git
cd cnd-mne-converter
uv sync --extra dev
```

A tiny example CND folder ships in the repo. Check that it opens:

```bash
uv run cnd-mne inspect tests/data/minimal-cnd --subject 1
```

You should see JSON for two trials, four EEG channels, and two stimulus tracks (`Speech Envelope`, `Word Onsets`). `inspect` only reads the MATLAB; it does not need a unit.

## Convert CND to MNE

The bundled example already declares `uV`, so this runs as-is:

```python
from cnd_mne import read_cnd_mne

rec = read_cnd_mne("tests/data/minimal-cnd", subject=1)
rec.raws[0].plot()
```

`rec.raws` is one MNE `Raw` per trial. `rec.cnd` is the original CND information.

Most public CND files do **not** declare a unit. Then you must pass one that the data owner actually confirmed:

```python
rec = read_cnd_mne("/path/to/dataCND", subject=1, neural_unit="uV")
```

If a subject file has more than one recording type:

```python
from cnd_mne import available_neural_variables

print(available_neural_variables("/path/to/dataSub1.mat"))
rec = read_cnd_mne("/path/to/dataSub1.mat", neural_variable="eeg", neural_unit="uV")
```

The unused type stays on `rec.cnd.additional_variables` and is written back on export. Trials are not joined and stimulus tracks are not resampled unless you ask. Missing electrode locations become names like `EEG001` and there is no montage (no map of where sensors sat on the head).

Optional views (names come from the CND file; these are the ones in the bundled example):

```python
envelope = rec.stimulus_raws("Speech Envelope")
words = rec.stimulus_annotations("Word Onsets")
eog = rec.external_raws(unit="uV", channel_types="eog")
continuous = rec.concatenate()  # opt-in; fake joins are marked
```

## Convert MNE back to CND

If you started from CND, write back through that template so envelopes and trial order survive:

```python
rec.raws[0].filter(1, 15)
paths = rec.write_cnd(
    "converted/dataCND", subject=1, output_unit="uV", mat_version="7.3"
)
```

Existing files are left alone unless you pass `overwrite=True`.

MNE cannot invent speech envelopes. For data that never was CND, `from_mne(...)` builds a new recording and tells you what it could not represent.

## Check a whole dataset

```bash
uv run cnd-mne verify-dataset /path/to/dataset \
  --neural-unit uV \
  --output verification.json
```

`--serialized-round-trip` also writes and rereads MATLAB (slow, needs disk). `--strict-spec` is for new CND you created, not for messy legacy files. Only pass a unit the owner confirmed.

## How it works

```text
CND .mat files
    → MATLAB reader (v5 or v7.3)
    → CNDRecording (trials, stimulus tracks, extra fields)
    → MNE adapter
    → one Raw per trial, plus rec.cnd with everything else
```

Writing goes the other way. If you started from CND, that original file is the template, so envelopes and trial order come back. A bare MNE `Raw` cannot invent those.

The public CND files I actually ran are listed in [docs/results](docs/results/README.md) (1,026 neural files). [docs/dataset-compatibility.md](docs/dataset-compatibility.md) is the short version of what those files look like. Open questions for the lab are in [docs/questions-for-maintainers.md](docs/questions-for-maintainers.md).

## What's in this repo

The converter is small. GitHub looks busy because most files are reports from that catalogue run, not extra features. The EEG itself is not in git. A clone is under a megabyte; `uv sync` then makes a local `.venv`.

```text
src/cnd_mne/      the tool (read MATLAB, hold a recording, talk to MNE, write MATLAB)
tests/            unit tests plus a tiny fake CND folder for CI
docs/results/     JSON from verify-dataset on the public collections
docs/manifests/   checksums of the zips I downloaded
docs/             field mapping, questions, design notes
```

If you only want to use it, you need `src/` and the install files. The JSON under `docs/` is so someone else can see what was checked.

## What it will not do quietly

- Resample or truncate to hide a clock mismatch (AliceSpeech is 500 Hz neural / 50 Hz stimulus)
- Assume volts, millivolts, or µV
- Assume `chanlocs` are in metres, or that they are even EEGLAB channel structs (EEGLAB is another EEG toolbox)
- Drop unknown fields just because MNE has nowhere to put them

## More detail

- [CNSP dataset catalogue](https://cnsp-resources.readthedocs.io/en/latest/datasetsPage.html)
- [Di Liberto lab](https://www.diliberg.net/)
- [CND 1.0 spec](https://data.cnspworkshop.net/CND_Specifications.pdf)
- [What the public datasets actually look like](docs/dataset-compatibility.md)
- [Verification evidence](docs/results/README.md)
- [Field mapping](docs/field-mapping.md)
- [Questions that still need the lab / MNE people](docs/questions-for-maintainers.md)
- [CND 1.0 audit](docs/cnd-spec-audit.md)

## Development

```bash
uv run pytest --cov=cnd_mne
uv run ruff check .
uv run ruff format --check .
uv run mypy src/cnd_mne
```

Public datasets are not in git. Checksums for the files I used are in `docs/manifests/`. CI uses `tests/data/minimal-cnd`.
