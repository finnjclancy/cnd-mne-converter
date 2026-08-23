# Review of existing Python CND importers

Reviewed against the public source on 2026-08-23.

## Eelbrain

[`eelbrain.load.cnd`](https://github.com/Eelbrain/Eelbrain/blob/main/eelbrain/_io/cnd.py)
loads one neural or stimulus MATLAB file into Eelbrain `Dataset` and `NDVar`
objects. It constructs explicit time and sensor dimensions and supports external
channels and condition labels.

The current neural path indexes `chanlocs` directly, so a legacy dataset such as
AliceSpeech, which omits channel locations, is not covered by that code path.
The function is documented as experimental. No CND writer is exposed.

## NAPlib

[`naplib.io.load_cnd`](https://github.com/naplab/naplib-python/blob/main/naplib/io/load_cnd.py)
loads CND into a trial-oriented `naplib.Data` object. It can infer a matching
subject-specific or shared stimulus file, tolerates missing channel locations,
preserves several additional fields, and combines neural and stimulus trials.
Its source states that it was adapted from Eelbrain's reader.

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

## Decisions adopted here

- Keep the useful trial-oriented canonical representation.
- Infer shared and subject-specific stimulus paths, including a sibling
  `stimCND/` directory.
- Compare alignment in seconds and never truncate by sample count implicitly.
- Allow missing channel metadata while emitting an explicit warning.
- Require physical unit and coordinate choices at the MNE adapter boundary.
- Preserve a companion CND model so reverse export remains possible.
