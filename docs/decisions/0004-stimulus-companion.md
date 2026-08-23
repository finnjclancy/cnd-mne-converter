# ADR 0004: Keep stimulus features in a companion CND model

- Status: Accepted
- Date: 2026-08-23

## Context

CND stimulus features can be scalar envelopes, sparse onset vectors,
spectrograms, phonetic feature matrices, or musical expectation signals. They
can use a sampling rate different from the neural data. MNE `Raw` channel types
do not provide a faithful universal representation for these feature sets.

Forcing all features into `Raw` would make MNE filtering and channel-selection
operations treat experimental predictors like physiological channels. It would
also lose feature-axis metadata and complicate round-trip export.

## Decision

Keep stimulus features in `CNDStimulus`, indexed as
`feature -> trial -> ndarray`. `MNECNDRecording` pairs this companion data with
the MNE neural trials.

Sparse event features may later gain an opt-in conversion to MNE annotations,
but that will be a derived view rather than the canonical representation.

## Consequences

- Arbitrary continuous features and their native clock are preserved.
- A bare MNE `Raw` is intentionally not considered a lossless CND conversion.
- MNE-to-CND export requires the companion stimulus object or new stimulus
  metadata supplied by the caller.
