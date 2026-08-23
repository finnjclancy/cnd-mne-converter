# CND-MNE field mapping

This table records the implemented mapping and the scientific decisions still
requiring confirmation.

| CND concept | Canonical representation | MNE representation | Policy / risk |
| --- | --- | --- | --- |
| `eeg.data` | Tuple of `time x channels` arrays | One `RawArray` per trial, transposed to `channels x time` | No implicit concatenation or padding |
| `eeg.fs` | `CNDNeural.sfreq` | `Info["sfreq"]` | Direct mapping |
| Stored EEG values | Original numerical values plus optional `data_unit` | Floating-point volts | Unit must be declared or explicitly supplied |
| `eeg.dataType` | `CNDNeural.data_type` | MNE channel type | MVP supports EEG only; opaque legacy strings fall back to the variable name |
| `eeg.deviceName` | `CNDNeural.device_name` | Provenance in `Info["description"]` | MNE has no universal device-name field |
| `eeg.chanlocs` | Tuple of field-preserving dictionaries | Optional `DigMontage` | EEGLAB axis mapping and scale to metres are opt-in |
| `eeg.extChan` | Separate external trial arrays and description | Not converted in MVP | Channel type and names can be ambiguous |
| `eeg.origTrialPosition` | One-based stored values | Retained in companion model | Never collapse into bare `Raw` |
| `eeg.paddingStartSample` | Preserved verbatim | Not yet converted to annotations | Needed for precise stimulus onset alignment |
| `stim.data` | `feature -> trial -> ndarray` | Companion `CNDStimulus` | Never force arbitrary features into physiological channels |
| `stim.fs` | Independent stimulus sampling rate | Companion time base | It need not equal neural `sfreq` |
| `stim.names` | Feature names | Companion metadata | Direct mapping |
| `stim.stimIdxs` | Stored values or `None` | Companion trial metadata | Missing legacy values warn; ordinal one-based values are available as a derived view |
| `stim.condIdxs` | Numeric or string values | Companion trial metadata | Legacy AAD uses strings rather than numeric indices |
| `stim.condNames` | Optional condition labels | Companion metadata | Some datasets encode labels directly in `condIdxs` |
| `cndVersion` | Optional version metadata | Companion provenance | Public legacy datasets often omit it |
| Additional fields | `extra_fields` | Companion metadata | Preserved when MATLAB-serializable |

## Invariants

- Neural trial `i` remains paired with stimulus trial `i`.
- Trial order and original presentation order remain distinguishable.
- Neural and stimulus clocks remain separate.
- Alignment is compared using duration in seconds, never raw sample count.
- No unit conversion occurs without a declared input unit.
- No coordinate conversion occurs without an explicit transform and scale.
- Unsupported information is reported rather than silently discarded.

## One-based indices

The canonical model preserves CND values exactly as stored, including MATLAB's
one-based `stimIdxs` and `origTrialPosition`. This improves round-trip fidelity.
Python consumers can use `CNDStimulus.resolved_stimulus_indices`; when a legacy
file omits `stimIdxs`, it provides derived ordinal values `1..n` without
pretending that the source file contained them.
