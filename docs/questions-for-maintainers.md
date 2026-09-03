# Questions for the lab / MNE people

These are things the converter will not guess. If we change behaviour, it should be because someone answered one of these, not because a default felt convenient.

## About the CND files

1. What physical unit is `eeg.data` in, for each public collection (or at least for one reference dataset)?
2. Should a later CND spec require `dataUnit` on neural and extra-channel groups?
3. `chanlocs`: units, axes, origin, frame? Metres? EEGLAB `(-Y, X, Z)`?
4. What is `paddingStartSample`? Is that padding part of the analysis window?
5. Empty trials — rejected trials that must keep their slot, or junk?
6. Extra channels (`extChan`): names, types (ref / EOG / audio / trigger), units, sampling rate, what to do when they are a different length from the EEG.
7. Attended vs unattended (AAD and similar): two files, or one paired stimulus object?
8. Which sparse features are events, and which are continuous TRF regressors?

## About the MNE API

1. Is "one `Raw` per variable-length trial + a companion object with the rest of the CND" acceptable?
2. Should MNE grow `read_cnd`, or should this stay a separate package?
3. Default return: separate trials, or a concatenated view with boundary annotations?
4. Continuous stimulus features: companion arrays, `misc` channels, or something new?
5. Which CND fields should become annotations vs info vs channel types?
6. Is export in scope for MNE? A random `Raw` does not contain envelopes or trial order.

## Scope

1. Wait for real MEG CND examples before pretending to support MEG?
2. Resampling / alignment: explicit derived-data step with provenance, or out of this package?
3. TRF-result files: later, after recording interchange is stable?
