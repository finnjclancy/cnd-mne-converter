# ADR 0002: Represent each CND trial as a separate MNE Raw object

- Status: Accepted
- Date: 2026-08-23

## Context

CND stores neural data as a cell array of `time x channels` trials. Trial
lengths can differ. MNE `Raw` represents one continuous timeline, while
`Epochs` normally represents equal-length trials.

Concatenating CND trials would create artificial joins. Filtering across those
joins could mix samples from unrelated recordings. Padding all trials to create
`Epochs` would invent data and obscure their true duration.

## Decision

The first adapter returns one `mne.io.RawArray` per CND trial, wrapped in
`MNECNDRecording`. Trial order remains the canonical model's order.

No implicit concatenation or padding is performed. A future explicit
concatenation helper may add boundary annotations and preserve the original
sample ranges.

## Consequences

- Variable-duration trials are represented without invented data.
- MNE operations are applied per trial unless the user explicitly combines
  them.
- The public API differs from conventional `mne.io.read_raw_*` readers that
  return one `Raw` object. This must be discussed before proposing an upstream
  MNE API.
