# Where the converter actually is

It reads and writes CND, and it has been run on every downloadable collection in the public catalogue — not just synthetic files. It is ready to show the lab. It is not ready for "the units are definitely microvolts" claims.

CND file → reader → `CNDRecording` → one MNE `Raw` per trial. The rest of the CND (stimulus clocks, trial order, extra channels, unknown fields) stays on the companion object so a write-back does not invent or drop it.

| | |
| --- | ---: |
| Neural files | 1,026 |
| Complete passes | 1,017 |
| Empty of neural samples | 8 (BabyRhythm) |
| Unreadable source file | 1 (SparrKULee1 `dataSub48.mat`) |
| Trials | 17,774 |
| Max numerical error on identity-test round trip | 0 |
| Tests | 116 |
| Statement coverage | 95.34% |

The eight empty files still parse. They just have no brain signal. The truncated HDF5 file is broken in the published zip, not in this converter.

What this does **not** settle: real EEG units, `chanlocs` frame, padding, attended/unattended pairing, extra-channel meaning, or whether MNE would take this API. Pick one subject, confirm those, compare against MATLAB. Details in [results](../results/README.md) and [questions](../questions-for-maintainers.md).
