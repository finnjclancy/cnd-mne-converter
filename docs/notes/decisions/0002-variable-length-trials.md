# Why one MNE Raw per trial

Accepted 23 August 2026.

CND trials can be different lengths. MNE `Raw` is one continuous timeline. `Epochs` wants equal lengths.

Gluing trials would create fake joins (filters would bleed across them). Padding to make Epochs would invent samples.

So the adapter returns one `Raw` per trial, on `MNECNDRecording`. `concatenate()` is opt-in. MNE marks the fake joins (`BAD boundary` / `EDGE boundary`); we also add `CND_TRIAL/*` and `trial_slices`.

This is different from `mne.io.read_raw_*`, which returns one `Raw`. That needs a conversation before anyone proposes it upstream.
