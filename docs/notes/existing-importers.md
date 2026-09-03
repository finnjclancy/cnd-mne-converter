# Other Python CND loaders

Looked at the public source and ran them on 26 August 2026.

## Eelbrain

[`eelbrain.load.cnd`](https://github.com/Eelbrain/Eelbrain/blob/main/eelbrain/_io/cnd.py)
loads one neural or stimulus MATLAB file into Eelbrain `Dataset` and `NDVar`
objects. It constructs explicit time and sensor dimensions and supports external
channels and condition labels.

The current neural path indexes `chanlocs` directly, so a legacy dataset such as
AliceSpeech, which omits channel locations, is not covered by that code path.
It also recognizes only the top-level variable `eeg` and expects external
channels at `extChan.data`. Eelbrain 0.41.2 loaded the two EEG trials from a
compatible form of the committed fixture. Its reader rejected the fixture's
valid EEGLAB struct-array `chanlocs` representation and squeezed single-channel
external arrays; these are reference-loader limitations, not failures of the
CND file. The function is documented as experimental. No CND writer is exposed.

## NAPlib

[`naplib.io.load_cnd`](https://github.com/naplab/naplib-python/blob/main/naplib/io/load_cnd.py)
loads CND into a trial-oriented `naplib.Data` object. It can infer a matching
subject-specific or shared stimulus file, tolerates missing channel locations,
preserves several additional fields, and combines neural and stimulus trials.
Its source states that it was adapted from Eelbrain's reader.

NAPlib 2.6.0 was also run against the committed fixture with truncation
disabled. It loaded both EEG trials with the expected `(100, 4)` and `(125, 4)`
shapes. Its neural path likewise recognizes only the top-level variable `eeg`
and assumes external samples live at `extChan.data`.

The default `truncate_lengths=True` path finds the minimum raw sample count
across EEG and all stimulus features. That is not generally safe for CND:
AliceSpeech stores EEG at 500 Hz and features at 50 Hz. Equal durations therefore
have approximately ten times as many neural samples, and sample-count truncation
would remove most of the EEG trial. No CND-specific writer is exposed.

## Shared lessons

- Both projects demonstrate the core MATLAB structure parsing.
- Both preserve CND's `time x channels` arrays in their own trial-oriented data
  types rather than producing MNE `Raw` objects.
- Both use the EEGLAB-style axis mapping `(-Y, X, Z)` for sensor positions.
- Neither resolves missing physical units or coordinate units.
- Neither provides the complete bidirectional CND <-> MNE round trip targeted by
  this project.
- Neither implements the CND 1.0 provision for one variable per recording
  modality or the specified `extChan.<type>` field-per-group layout.

## Decisions adopted here

- Keep the useful trial-oriented canonical representation.
- Infer shared and subject-specific stimulus paths, including a sibling
  `stimCND/` directory.
- Compare alignment in seconds and never truncate by sample count implicitly.
- Allow missing channel metadata while emitting an explicit warning.
- Require physical unit and coordinate choices at the MNE adapter boundary.
- Preserve a companion CND model so reverse export remains possible.
- Allow callers to list and select modality variables; preserve every
  unselected top-level variable during template-backed export.
- Parse and reconstruct both the legacy `extChan.data` convention and the CND
  1.0 named-field convention, with deterministic group ordering across MATLAB
  encodings.
