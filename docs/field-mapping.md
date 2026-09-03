# Field mapping

What a CND field becomes in this package. If you do not pass extra arguments, some of this stays a guess (units, coordinate frame).

| CND | Inside the package | In MNE | Notes |
| --- | --- | --- | --- |
| `eeg.data` | time × channels arrays | one `Raw` per trial (`channels × time`) | trials are not glued or padded |
| `eeg.fs` | `sfreq` | `Info["sfreq"]` | copied as-is |
| stored EEG values | original numbers + optional unit | MNE wants volts | you must declare or pass the unit |
| `eeg.dataType` | `data_type` | channel type `eeg` | weird MATLAB strings fall back to the variable name |
| fNIRS `data` grid | combined trials, original block sizes kept | HbO `hbo`, HbR `hbr`, HbT `misc` | the grid is rebuilt on write-back |
| fNIRS `datatype` | signal types + channels per type | names and types | MNE has no HbT type, so those channels stay `misc` |
| stored fNIRS values | original numbers + optional unit | molar concentration | `M` / `mM` / `uM` / `nM` if you pass them |
| `eeg.deviceName` | `device_name` | stuffed into `Info["description"]` | MNE has no proper device field |
| `eeg.chanlocs` | dicts, original fields kept | optional `DigMontage` | EEGLAB axes and metres are opt-in |
| 2D topomap `chanlocs` | real labels + raw layout | names only | `COMNT`/`SCALE` are drawing helpers, not electrodes |
| `eeg.extChan` | separate arrays | not mixed into the EEG `Raw` unless you ask | types/units can be unclear |
| `extChan.<type>` named groups | combined in a stable order | same, as an extra view | v5 and v7.3 return struct fields in different orders, so groups are sorted by name |
| `eeg.origTrialPosition` | one-based values as stored | stays on `rec.cnd` | never folded into a bare `Raw` |
| `eeg.paddingStartSample` | kept as-is | not annotations yet | needed if you care about stimulus onset vs padding |
| `stim.data` | feature → trial → array | `rec.cnd` plus optional `misc` views | envelopes are not EEG channels |
| `stim.fs` | its own rate | stimulus-view time base | CND 1.0 wants this equal to neural `fs`; Alice is not |
| `stim.names` | feature names | metadata | copied |
| `stim.stimIdxs` | stored values or missing | metadata | AAD omits this |
| `stim.condIdxs` | numbers or strings | metadata | AAD uses strings |
| `stim.condNames` | optional labels | metadata | sometimes the label is already in `condIdxs` |
| `cndVersion` | optional number | metadata | public files often skip it |
| extra fields | `extra_fields` | on `rec.cnd` | kept if MATLAB can write them |
| other top-level modalities | `additional_variables` | not the selected `Raw` | they come back on template write |

## Rules we do not break quietly

- Neural trial `i` stays paired with stimulus trial `i`
- Presentation order (`origTrialPosition`) is separate from file order
- Neural and stimulus clocks stay separate. A mismatch is a warning, or an error with `--strict-spec`
- We compare duration in seconds, not raw sample counts
- Empty trials and one-sample-off features stay as they are (warn). Strict mode rejects them
- No unit or coordinate conversion unless you asked
- Unknown fields are reported, not dropped
- If a subject file has extra modalities, the ones you did not open still survive a round trip

## One-based indices

MATLAB counts from 1. We keep `stimIdxs` and `origTrialPosition` that way. Python code that wants a filled-in list can use `CNDStimulus.resolved_stimulus_indices` — if the file omitted `stimIdxs`, that helper invents `1..n` and does not pretend the file contained them.
