# Why stimulus tracks stay on rec.cnd

Accepted 23 August 2026.

CND stimulus features can be envelopes, sparse onsets, spectrograms, phonetic matrices, musical expectation, and they can run on a different clock from the EEG. Stuffing all of that into MNE `Raw` would make filters treat predictors like brain channels, and you would lose feature-axis metadata on the way back.

So features live in `CNDStimulus` as `feature → trial → array`. `stimulus_raws()` is an optional view (`misc` channels, stimulus clock). Sparse events can become annotations later; that would still be a view, not the source of truth.

A bare `Raw` is not a lossless CND conversion. Export needs `rec.cnd` or new stimulus metadata from you.
