# Proposed MNE-facing API

## Status

This is a concrete discussion proposal, not a claim that MNE has accepted the
API. It is backed by the standalone implementation and public-catalogue test
matrix.

MNE's current I/O convention is important here: functions under `mne.io` are
normally named `read_raw_*`, return a single `Raw`, and can participate in the
generic [`mne.io.read_raw`](https://mne.tools/stable/generated/mne.io.read_raw.html)
dispatcher. CND does not naturally satisfy that contract because it can contain
multiple variable-length trials and separate stimulus clocks. MNE also notes a
similar limitation for flexible multi-stream XDF data in its
[EEG import guide](https://mne.tools/stable/auto_tutorials/io/20_reading_eeg_data.html).
No existing CND reader or open CND issue was found in the MNE repository during
the 26 August 2026 review.

## Proposed reader

```python
recording = read_cnd_mne(
    path,
    subject=1,
    neural_unit="uV",  # required when absent from the source
    montage="none",  # no coordinate guess
)
```

The return value is an `MNECNDRecording` companion object:

- `raws`: one MNE `Raw` per CND neural trial;
- `cnd`: the loss-aware canonical CND representation;
- `trial_metadata`: paired condition, order, sample-count, and duration data;
- `stimulus_raws(feature)`: opt-in MNE `misc` views on the stimulus clock;
- `stimulus_annotations(feature)`: opt-in sparse-event views;
- `external_raws(...)`: explicitly named, typed, and scaled external views; and
- `concatenate()`: an explicit continuous view with MNE boundary annotations.

## Why the reader should not return one bare `Raw`

A bare `Raw` cannot losslessly express all observed CND data:

- trials can have unequal lengths;
- neural and stimulus sampling frequencies can differ;
- multiple multidimensional stimulus features can share a trial;
- empty rejected trials can retain their ordinal positions;
- external channels can have unknown types, units, or unequal lengths; and
- conditions and experiment-specific fields must survive export.

Implicit concatenation, padding, resampling, or channel typing would therefore
make scientific decisions while reading a file. The companion result keeps
ordinary MNE analysis available without discarding the original experiment
structure.

## Proposed export policy

Template-backed export is safe when MNE processing preserves trial count,
channel order, sampling rate, and trial lengths:

```python
recording.raws[0].filter(1, 15)
recording.write_cnd("derived/dataCND", output_unit="uV")
```

Constructing CND from unrelated MNE data is also supported, but the caller must
provide stimulus and experiment metadata that cannot be inferred. Unsupported
MNE metadata can warn or raise rather than disappear silently.

## Suggested upstream contribution sequence

1. Ask on the MNE forum whether CND belongs in core MNE, following the current
   [contribution guidance](https://mne.tools/stable/development/contributing.html).
2. If maintainers agree that core changes are appropriate, open a design issue
   using the tested companion-object behavior.
3. Agree on return type, naming, supported scope, and dependency strategy.
4. Contribute the low-level reader and small redistributable fixtures.
5. Add the MNE adapter and documentation in a separate reviewable change.
6. Consider export only after the import representation is accepted.
7. Treat TRF result interchange as a separate proposal.

## Questions for maintainers

- Should this live in MNE itself or remain an interoperability package?
- Is a specialized result containing one `Raw` per trial acceptable?
- If MNE requires a single-`Raw` contract, should core support be a deliberately
  lossy neural-only reader while the companion package retains full CND data?
- Should a convenience API default to separate trials or require explicit
  concatenation?
- Where should continuous naturalistic stimulus features live in MNE?
- Is CND export within MNE's scope?
- What is the smallest first contribution the maintainers would review?
