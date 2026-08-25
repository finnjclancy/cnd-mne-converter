# Decisions needed from CND and MNE maintainers

The converter deliberately avoids defaults for the questions below. Answers
should be recorded in an architecture decision before behavior changes.

## CND scientific semantics

1. What physical unit is intended for `eeg.data` in each public collection?
2. Should a future CND revision require `dataUnit` for neural and external
   channel groups?
3. What units, axes, origin, and frame apply to `chanlocs`?
4. What does `paddingStartSample` measure, and does padding remain part of the
   analysis interval?
5. Are empty trials rejected trials that must retain their ordinal position?
6. How should multiple external-channel groups declare names, types, units,
   sampling frequencies, and references?
7. How should attended/unattended alternatives and other parallel stimulus
   representations be paired?
8. Which sparse features are events, and which must remain continuous model
   regressors?

## Proposed MNE representation

1. Is a specialized object containing one `Raw` per variable-length trial plus
   a lossless CND companion model acceptable?
2. Should MNE expose `read_cnd`, or should this remain a separate package?
3. Should the primary API return separate trials or a boundary-annotated
   concatenated view?
4. Should continuous stimulus features remain companion arrays, be represented
   as `misc` channels, or use a new naturalistic-experiment abstraction?
5. Which CND fields should map to MNE annotations, metadata, or channel types?
6. Is export within scope for MNE, given that arbitrary `Raw` objects do not
   contain the stimulus and experiment information required by CND?

## Scope decisions

1. Should MEG and other modalities wait for real CND examples and maintainers
   with modality expertise?
2. Should resampling and alignment be implemented as explicit derived-data
   operations with provenance, or remain outside the converter?
3. Should TRF result interchange be a separate proposal after recording
   interchange is stable?
