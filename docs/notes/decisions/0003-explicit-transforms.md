# Why units, coordinates, and resampling are never guessed

Accepted 23 August 2026.

MNE wants EEG in volts and sensors in metres. The public CND files do not say. Some (AliceSpeech) also use different neural and stimulus rates, even though CND 1.0 wants them equal.

A wrong unit can be off by a million. A wrong axis can make a pretty but wrong map. Truncating by sample count is wrong when the clocks differ.

So:

- numbers stay as stored until you pass a unit
- no montage unless you ask; EEGLAB axes need an explicit scale to metres
- compare duration in seconds
- rate mismatch: warning normally, error with `--strict-spec`
- never resample, truncate, or pad unless you asked

Legacy files therefore need a couple of arguments. That is the point.
