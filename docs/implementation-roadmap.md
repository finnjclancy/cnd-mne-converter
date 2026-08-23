# Implementation roadmap

## Goal

Deliver a tested CND import/export layer that can support an upstream MNE
discussion without silently altering scientific data.

## Phase 1: structural prototype — implemented

- Canonical neural and stimulus dataclasses.
- MATLAB v5 reader and atomic writer.
- Dimension and duration validation.
- One EEG `RawArray` per CND trial.
- Explicit volts conversion.
- Conservative MNE-to-CND model conversion.
- CLI structural inspection.
- Synthetic round-trip tests.
- Full structural scans of four public datasets (76 subject files).

## Phase 2: scientific mapping decisions

Resolve with the CND maintainers:

1. What physical unit is intended for `eeg.data` in the public datasets?
2. Should a future CND version require a `dataUnit` field?
3. What coordinate unit and frame are intended for `chanlocs`?
4. How should pre/post-stimulus padding be represented and validated?
5. Is a list of `Raw` objects acceptable, or should an MNE-facing convenience
   view concatenate trials with boundary annotations?
6. Should word/note onset vectors gain a derived `Annotations` view?
7. How should multiple stimulus alternatives, such as attended and unattended
   envelopes, be represented?

No default conversion should be added until each default has a defensible
answer.

## Phase 3: broaden compatibility

- MATLAB v7.3/HDF5 structures.
- Explicit external-channel mapping for mastoids, EOG, EMG, and miscellaneous
  channels.
- Padding-aware alignment metadata.
- Optional, provenance-recorded resampling.
- Optional concatenated `Raw` view with boundary annotations.
- Support for MEG and fNIRS only after defining modality-specific metadata.
- Memory-aware or lazy reading for multi-gigabyte datasets.

## Phase 4: validation matrix

For every available CND dataset, record:

- MATLAB version and top-level variables;
- subject, trial, channel, and feature counts;
- neural and stimulus sampling frequencies;
- declared unit and coordinate metadata;
- condition and trial-index representation;
- external channels and padding;
- parser/validator result;
- MNE construction result after units are confirmed; and
- numerical round-trip error.

Large data should be cached outside the repository. CI should use small fixtures;
full-dataset tests should run locally or in a separately provisioned workflow.

## Phase 5: upstream strategy

1. Stabilize this package and its compatibility report.
2. Open a design discussion with MNE maintainers before proposing code.
3. Agree whether MNE should expose a specialized `read_cnd` result, a list of
   `Raw` objects, or only a lower-level reader.
4. Split a contribution into reviewable pieces: reader, tests, documentation,
   and potentially export support.
5. Treat TRF-result interchange as a separate proposal after data interchange
   is reliable.

## Definition of done for the first research milestone

- Lalor, Alice, AAD, and MusicImagery all parse with documented warnings only.
- A confirmed-unit subset converts to MNE and produces sensible channel/time
  metadata and plots.
- Supported synthetic data survives CND -> MNE -> CND within numerical
  tolerance.
- Every implicit loss or unsupported field is visible in validation output.
- Architecture decisions and unresolved questions are suitable for discussion
  with Giovanni Di Liberto and MNE maintainers.
