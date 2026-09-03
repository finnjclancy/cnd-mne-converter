# Scientific checks

A round trip passing does not mean the recording is correctly scaled. Someone who knows the experiment still has to tick these.

## Source

- URL, archive checksum, dataset version, licence, any participant-data restrictions
- Neural and stimulus files from the same release
- What preprocessing was already applied before CND

## Neural values

- Physical unit on every neural and extra-channel group
- Channel type, reference, sampling rate, filters, bad channels
- Spot-check samples against MATLAB or the acquisition export, before and after conversion
- MNE plots and amplitudes should look plausible in SI units

## Sensors

- Coordinate unit, axes, origin, frame
- Plot the montage and check a few known electrodes
- Do not turn on the EEGLAB-to-MNE transform just because the map "looks right"

## Trials and stimuli

- Trial order, rejected trials, original positions, padding, duration differences
- Stimulus clock; are onsets events or continuous regressors?
- Attended/unattended alternatives and condition labels
- At least three known event times against the experiment log or audio

## Independent comparison

- Same subject in the original MATLAB code, and NAPlib/Eelbrain if they apply
- Shapes, channel order, trial order, rates, amplitudes, stimulus values, event times
- One representative MNE analysis vs an existing reference
- Export to CND, reopen it independently, compare the fields that should survive

## Sign-off

Write down dataset, subject, source checksums, converter version, MNE version, the unit and coordinate arguments you passed, tolerances, who reviewed it, date, leftover caveats. Keep that next to the verification JSON.
