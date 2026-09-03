# MNE API proposal

This is what I would take to the MNE people. They have not agreed to it.

MNE's `read_raw_*` functions return one `Raw`. CND often has several variable-length trials and a separate stimulus clock, so that contract does not fit. XDF has a similar problem in the [MNE EEG import guide](https://mne.tools/stable/auto_tutorials/io/20_reading_eeg_data.html). I did not find an existing CND reader in MNE as of 26 August 2026.

```python
recording = read_cnd_mne(
    path,
    subject=1,
    neural_unit="uV",  # required when the file does not say
    montage="none",
)
```

You get an `MNECNDRecording`:

- `raws` — one `Raw` per neural trial
- `cnd` — the rest of the file
- `stimulus_raws(feature)` / `stimulus_annotations(feature)` / `external_raws(...)`
- `concatenate()` — opt-in, with markers on the fake joins

Returning one bare `Raw` would mean silently concatenating, padding, resampling, or dropping stimulus data. That is a scientific decision, not an I/O detail.

Export after a CND import uses the original file as a template:

```python
recording.raws[0].filter(1, 15)
recording.write_cnd("derived/dataCND", output_unit="uV")
```

Building CND from unrelated MNE data is possible, but you have to supply the stimulus/experiment bits MNE does not have.

If they want it in core: ask on the forum, then a design issue, then a small reader + fixtures, then the adapter, export later, TRF files later still. [Contribution guide](https://mne.tools/stable/development/contributing.html).

Open questions: in MNE or a separate package? One `Raw` per trial ok? If they insist on a single `Raw`, should core be a lossy neural-only reader? Default to separate trials or concatenated? Where do continuous stimulus features live? Is export in scope?
