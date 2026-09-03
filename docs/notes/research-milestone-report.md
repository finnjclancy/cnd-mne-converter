# Where the converter actually is

It reads and writes CND. I ran it on every downloadable collection in the public catalogue, not just fake files. Fine to show the lab. Not fine to claim "these values are definitely microvolts".

Path: CND file → reader → `CNDRecording` → one MNE `Raw` per trial. Stimulus clocks, trial order, extra channels, and unknown fields stay on `rec.cnd` so write-back does not invent or drop them.

| | |
| --- | ---: |
| Neural files | 1,026 |
| Pass | 1,017 |
| Empty (BabyRhythm) | 8 |
| Unreadable (SparrKULee1 `dataSub48.mat`) | 1 |
| Trials | 17,774 |
| Max numerical error on the dummy-unit round trip | 0 |
| Tests | 116 |
| Statement coverage | 95.34% |

The eight empty files still parse. They just have no brain signal. The truncated HDF5 file is broken in the published zip.

This does not settle: real EEG units, `chanlocs` frame, padding, attended/unattended pairing, what extra channels are, or whether MNE would take this API. Pick one subject, confirm those, compare against MATLAB. See [results](../results/README.md) and [questions](../questions-for-maintainers.md).
