# CND-MNE field mapping

This is the initial mapping hypothesis. Each row must be confirmed against the
CND specification, representative datasets, and MNE conventions before the API
is considered stable.

| CND concept | Proposed MNE representation | Transformation | Risk |
| --- | --- | --- | --- |
| `neural.data` | One `RawArray` per trial, or concatenated `RawArray` | Transpose from time x channels to channels x time | Trial boundaries must remain explicit |
| `neural.fs` | `Info["sfreq"]` | Direct mapping | Neural and stimulus rates must agree |
| `neural.dataType` | MNE channel types | Normalize CND modality names | Unknown modalities need a fallback |
| `neural.deviceName` | Device metadata and provenance | Normalize known devices | No exact universal field mapping |
| `neural.chanlocs` | `DigMontage` | Convert EEGLAB coordinates and coordinate frame | Naive conversion can move sensors |
| `neural.extChan` | Typed MNE channels | Map EOG, mastoid, and other external channels | Type names may be ambiguous |
| `neural.origTrialPosition` | Trial metadata | Preserve original presentation order | Lost if only a bare `Raw` is retained |
| `stim.data` | Companion stimulus feature collection | Preserve feature-set and trial axes | No natural home in a bare `Raw` |
| `stim.names` | Stimulus feature metadata | Direct mapping | None when the companion model is retained |
| `stim.stimIdxs` | Trial metadata | Direct mapping | Must remain aligned after reordering |
| `stim.condIdxs` and `condNames` | Trial metadata and annotations | Encode condition identity | Avoid lossy string-only encoding |
| `cndVersion` | Canonical model metadata | Direct mapping | Required for version-aware parsing |
| Additional fields | `extra_fields` | Preserve recursively | Must remain MATLAB-serializable |

## Required invariants

- Neural trial `i` remains paired with stimulus trial `i`.
- Neural and stimulus sample `i` represent the same time point.
- Sampling frequencies match unless an explicit conversion policy is applied.
- Trial order and original presentation order remain distinguishable.
- Unit and coordinate transformations are explicit and reversible where
  possible.
- Unsupported information is reported rather than silently discarded.
