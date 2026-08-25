# Scientific validation checklist

Structural round trips are necessary but do not establish that an imported
recording is scientifically scaled or interpreted correctly. A dataset is
ready for scientific claims only after the applicable checks below are signed
off by someone familiar with the experiment.

## Source provenance

- Record the source URL, archive checksum, dataset version, licence, and any
  participant-data restrictions.
- Confirm that the neural and stimulus files belong to the same release.
- Record preprocessing already applied before CND creation.

## Neural values

- Confirm the physical unit stored in every neural and external channel group.
- Confirm channel type, reference, sampling rate, filters, and bad channels.
- Compare selected samples against MATLAB or the acquisition export before and
  after conversion.
- Confirm that MNE plots and summary amplitudes are plausible in SI units.

## Sensors and coordinates

- Confirm coordinate unit, axis orientation, origin, and coordinate frame.
- Plot the montage and check identifiable electrodes independently.
- Do not enable the EEGLAB-to-MNE transform from visual plausibility alone.

## Trials and stimuli

- Confirm trial order, rejected trials, original positions, padding, and
  duration differences.
- Confirm the stimulus clock and whether onset vectors are events or continuous
  regressors.
- Confirm attended/unattended alternatives and condition labels.
- Verify at least three known event times against the experiment log or audio.

## Independent comparison

- Load the same subject with the original MATLAB code and, where applicable,
  NAPlib or Eelbrain.
- Compare shapes, channel order, trial order, sampling rates, amplitudes,
  stimulus values, and event times.
- Run one representative MNE analysis and compare its result with an existing
  reference analysis.
- Export to CND, reopen it independently, and compare the fields that are
  expected to survive.

## Sign-off record

Record the dataset, subject, source checksums, converter version, MNE version,
explicit unit and coordinate arguments, numerical tolerances, reviewer, date,
and unresolved caveats. Keep that record with the generated verification JSON.
