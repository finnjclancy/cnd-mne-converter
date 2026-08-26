# CND-MNE field mapping

This table records the implemented mapping and the scientific decisions still
requiring confirmation.

| CND concept | Canonical representation | MNE representation | Policy / risk |
| --- | --- | --- | --- |
| `eeg.data` | Tuple of `time x channels` arrays | One `RawArray` per trial, transposed to `channels x time` | No implicit concatenation or padding |
| `eeg.fs` | `CNDNeural.sfreq` | `Info["sfreq"]` | Direct mapping |
| Stored EEG values | Original numerical values plus optional `data_unit` | Floating-point volts | Unit must be declared or explicitly supplied |
| `eeg.dataType` | `CNDNeural.data_type` | MNE `eeg` channel type | Opaque legacy strings fall back to the variable name |
| fNIRS `data` signal-type x trial grid | Combined `time x channels` trials plus retained block sizes | HbO `hbo`, HbR `hbr`, and HbT `misc` channels | The original grid is reconstructed during template-backed export |
| fNIRS `datatype` | `signal_types` and `channels_per_signal_type` | Deterministic channel names and types | MNE has no HbT type; its values and CND label are preserved without mislabelling it HbO/HbR |
| Stored fNIRS values | Original values plus optional `data_unit` | Floating-point molar concentrations | Unit must be declared or explicitly supplied; `M`, `mM`, `uM`, and `nM` are supported |
| `eeg.deviceName` | `CNDNeural.device_name` | Provenance in `Info["description"]` | MNE has no universal device-name field |
| `eeg.chanlocs` | Tuple of field-preserving dictionaries | Optional `DigMontage` | EEGLAB axis mapping and scale to metres are opt-in |
| 2D topomap-layout `chanlocs` | Real channel labels plus retained raw layout | Channel names only | `COMNT`/`SCALE` drawing helpers are excluded; global outline/mask data is preserved for export |
| `eeg.extChan` | Separate external trial arrays, description, and additional fields | Retained in companion model, not added to neural `Raw` by default | Channel type, names, and units can be ambiguous |
| `extChan.<type>` named groups | Deterministically combined trials plus retained names and channel counts | Same explicit external-channel view | Alphabetical group order is used because v5/v7.3 readers expose MATLAB struct fields in different orders |
| `eeg.origTrialPosition` | One-based stored values | Retained in companion model | Never collapse into bare `Raw` |
| `eeg.paddingStartSample` | Preserved verbatim | Not yet converted to annotations | Needed for precise stimulus onset alignment |
| `stim.data` | `feature -> trial -> ndarray` | Companion `CNDStimulus`; optional `misc` `RawArray` views | Never force arbitrary features into physiological channels |
| `stim.fs` | Independent stimulus sampling rate | Companion and stimulus-view time base | CND 1.0 requires equality with neural `fs`; tolerant mode preserves observed legacy mismatches |
| `stim.names` | Feature names | Companion metadata | Direct mapping |
| `stim.stimIdxs` | Stored values or `None` | Companion trial metadata | Missing legacy values warn; ordinal one-based values are available as a derived view |
| `stim.condIdxs` | Numeric or string values | Companion trial metadata | Legacy AAD uses strings rather than numeric indices |
| `stim.condNames` | Optional condition labels | Companion metadata | Some datasets encode labels directly in `condIdxs` |
| `cndVersion` | Optional numeric version metadata | Companion provenance | Numeric type is preserved; public legacy datasets often omit it |
| Additional fields | `extra_fields` | Companion metadata | Preserved when MATLAB-serializable |
| Additional top-level modality variables | `CNDRecording.additional_variables` | Retained beside the selected MNE modality | Caller selects one variable; all others survive template-backed export |

## Invariants

- Neural trial `i` remains paired with stimulus trial `i`.
- Trial order and original presentation order remain distinguishable.
- Neural and stimulus clocks remain separate in memory; a mismatch is a CND 1.0
  conformance warning or strict-mode error.
- Alignment is compared using duration in seconds, never raw sample count.
- Legacy empty trials and unequal feature lengths are preserved with warnings;
  strict validation rejects those CND conformance deviations.
- No unit conversion occurs without a declared input unit.
- No coordinate conversion occurs without an explicit transform and scale.
- Unsupported information is reported rather than silently discarded.
- A subject file with multiple modality variables never loses the unselected
  variables during a controlled round trip.

## One-based indices

The canonical model preserves CND values exactly as stored, including MATLAB's
one-based `stimIdxs` and `origTrialPosition`. This improves round-trip fidelity.
Python consumers can use `CNDStimulus.resolved_stimulus_indices`; when a legacy
file omits `stimIdxs`, it provides derived ordinal values `1..n` without
pretending that the source file contained them.
