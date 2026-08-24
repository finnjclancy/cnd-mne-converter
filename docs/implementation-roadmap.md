# Implementation roadmap

## Goal

Deliver a tested CND import/export layer that can support an upstream MNE
discussion without silently altering scientific data.

## Phase 1: structural prototype — implemented

- Canonical neural and stimulus dataclasses.
- MATLAB v5 and v7.3/HDF5 readers plus an atomic MATLAB v5 writer.
- Dimension and duration validation.
- One EEG `RawArray` per CND trial.
- Explicit volts conversion.
- Conservative MNE-to-CND model conversion.
- CLI structural inspection.
- Synthetic round-trip tests.
- Full structural scans of six public datasets (142 non-empty subject files).

## Phase 1b: tested interoperability milestone — implemented

- End-to-end verification of 142 subjects and 3,008 trials.
- MNE Welch PSD smoke tests for every subject.
- MNE views for all univariate and multivariate stimulus features.
- Template-backed round trips with zero observed numerical error.
- Explicit continuous view with protected MNE boundary annotations.
- Tolerant legacy and strict CND 1.0 validation modes.
- Committed MATLAB fixture, FIF interoperability test, JSON evidence, and CI.
- Numeric `cndVersion` and squeezed one-channel parser fixes.

## Phase 2: scientific mapping decisions

Resolve with the CND maintainers:

1. What physical unit is intended for `eeg.data` in the public datasets?
2. Should a future CND version require a `dataUnit` field?
3. What coordinate unit and frame are intended for `chanlocs`?
4. How should pre/post-stimulus padding be represented and validated?
5. Is the implemented list of `Raw` objects plus an explicit boundary-annotated
   concatenated view acceptable for an upstream MNE API?
6. Should word/note onset vectors gain a derived `Annotations` view in addition
   to the implemented `misc`-channel stimulus view?
7. How should multiple stimulus alternatives, such as attended and unattended
   envelopes, be represented?

No default conversion should be added until each default has a defensible
answer.

## Phase 3: broaden compatibility

- Broader MATLAB v7.3/HDF5 layout coverage and optional v7.3 writing.
- Explicit external-channel mapping for mastoids, EOG, EMG, and miscellaneous
  channels.
- Padding-aware alignment metadata.
- Optional, provenance-recorded resampling.
- Optional concatenated `Raw` view with boundary annotations.
- Support for MEG and fNIRS only after defining modality-specific metadata.
- Memory-aware or lazy reading for multi-gigabyte datasets.

## Phase 4: validation matrix — implemented for the first six archives

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

Large data are cached outside Git history and mirrored as GitHub release assets.
CI uses small fixtures; the reproducible full-dataset verifier runs locally and
stores machine-readable reports under `docs/results/`.

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

- [x] Lalor natural/reversed, Alice, AAD, MusicImagery, and SparrKULee2 parse
  with documented warnings only.
- [x] All 142 non-empty subjects pass structural MNE, PSD, stimulus-view, and controlled
  round-trip checks under a recorded identity-test unit assumption.
- [ ] A confirmed-unit subset produces scientifically scaled plots and summary
  statistics.
- [x] Supported synthetic and public data survive CND -> MNE -> CND within
  numerical tolerance.
- [x] Unsupported MNE metadata and CND conformance deviations are visible.
- [x] Architecture decisions, JSON evidence, and unresolved questions are
  suitable for discussion with Giovanni Di Liberto and MNE maintainers.
