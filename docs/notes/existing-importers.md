# Other Python CND loaders

I looked at the public source and ran them on 26 August 2026.

## Eelbrain

[`eelbrain.load.cnd`](https://github.com/Eelbrain/Eelbrain/blob/main/eelbrain/_io/cnd.py) loads one neural or stimulus MATLAB file into Eelbrain `Dataset` / `NDVar` objects. Time and sensor dimensions are explicit. Extra channels and condition labels are supported.

It indexes `chanlocs` directly, so AliceSpeech (no channel locations) does not go down that path. It only looks at a top-level `eeg` variable, and extra channels have to live at `extChan.data`.

Eelbrain 0.41.2 loaded the two EEG trials from a compatible form of our committed fixture. It rejected the fixture's valid EEGLAB struct-array `chanlocs` and squeezed single-channel extra arrays. Those are limits of that reader, not of the CND file. The function is documented as experimental. No writer.

## NAPlib

[`naplib.io.load_cnd`](https://github.com/naplab/naplib-python/blob/main/naplib/io/load_cnd.py) loads CND into a trial-oriented `naplib.Data` object. It can find a matching stim file (shared or per-subject), tolerate missing channel locations, keep some extra fields, and combine neural + stimulus trials. The source says it was adapted from Eelbrain.

NAPlib 2.6.0, with truncation off, loaded both EEG trials from our fixture with shapes `(100, 4)` and `(125, 4)`. Same limits: only top-level `eeg`, extra samples at `extChan.data`.

Default `truncate_lengths=True` takes the shortest raw sample count across EEG and every stimulus feature. That is unsafe for CND. AliceSpeech is 500 Hz EEG / 50 Hz features, so equal duration means ~10× as many neural samples. Truncating by sample count would throw away most of the EEG. No writer.

## What I took from that

- Both parse the core MATLAB layout
- Both keep `time × channels` in their own types, not MNE `Raw`
- Both use EEGLAB `(-Y, X, Z)` for sensors
- Neither solves units or coordinate units
- Neither does a full CND ↔ MNE round trip
- Neither does "one variable per modality" or named `extChan.<type>` groups

## What this package does instead

- Keep a trial-oriented in-memory model
- Find shared and subject-specific stim paths, including a sibling `stimCND/` folder
- Compare alignment in seconds, never truncate by sample count unless asked
- Missing channel metadata is a warning, not a crash
- Units and coordinates are required at the MNE boundary
- Keep `rec.cnd` so write-back is possible
- List/select modality variables; keep the unused ones on export
- Parse both legacy `extChan.data` and CND 1.0 named groups, same order in v5 and v7.3
