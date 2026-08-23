# Observed public dataset compatibility

The table below records a structural scan of every subject file in four public
archives. This is not scientific validation of the datasets or their physical
units.

| Dataset | Subjects scanned | Trials per subject | Neural / stimulus rate | Channels | Features | Important variation | Prototype result |
| --- | ---: | ---: | --- | ---: | ---: | --- | --- |
| LalorNatSpeech | 19 | 20 | 128 / 128 Hz | 128 | 4 | Channel locations, mastoids, multidimensional spectrogram and phonetic features; EEG is 1.07-2.86 s longer than stimulus | Reads and validates with explicit duration and unit warnings |
| AliceSpeech | 20 | 12 | 500 / 50 Hz | 60 | 2 | No channel names or locations; no external channels; clocks align by duration rather than sample count | Reads and validates; generated MNE channel names required |
| AAD KULeuven | 16 | 8 | 32 / 32 Hz | 64 | 1 per stimulus file | Subject-specific `stimCND/dataStimN.mat`; separate unattended envelope; missing `stimIdxs`; string conditions; rich subject fields | Reads and validates; missing indices reported and metadata preserved |
| MusicImagery | 21 | 88 | 64 / 64 Hz | 64 | 2 | Listening and imagery conditions; opaque MATLAB `string` object in `dataType` | Reads and validates; modality safely inferred from top-level `eeg` variable |

All 76 subject files parsed without structural validation errors. The warnings
shown in the table are deliberate indicators of unresolved metadata or timing,
not parser failures.

## Cross-dataset findings

1. None of the four inspected legacy datasets declares `cndVersion`.
2. None declares an unambiguous EEG physical unit.
3. Sampling-rate equality cannot be required: Alice stores neural and stimulus
   features at a 10:1 rate ratio.
4. Sample-count truncation is not a general alignment solution.
5. Channel locations cannot be required because Alice omits them.
6. `stimIdxs` and numeric `condIdxs` cannot be assumed because AAD omits the
   former and uses string values for the latter.
7. Unknown neural fields matter. AAD contains attention ear, story, experiment,
   original sampling rate, and stimulus-track metadata.
8. MATLAB scalar strings are not uniform. MusicImagery contains an opaque MCOS
   string object for `dataType` even though ordinary strings are used elsewhere.

## Test levels

### Automated fixture tests

Small generated MATLAB files test:

- multiple variable-length neural trials;
- independent neural and stimulus rates;
- multidimensional stimulus features;
- channel locations and external channels;
- missing indices and string conditions;
- volts conversion and transposition; and
- CND -> MNE -> CND numerical round trips.

### Local integration tests

Full public datasets remain outside Git. The initial scan loaded each subject
sequentially to bound memory use. The `cnd-mne inspect` command provides the
detailed per-file report.

## Unresolved scientific questions

- Confirm stored EEG units for each public CND dataset with its documentation
  or data owner.
- Confirm coordinate unit and head-frame semantics for EEGLAB-style
  `chanlocs`.
- Define the meaning of neural samples before and after the stimulus, including
  datasets with and without `paddingStartSample`.
- Decide how attended and unattended AAD stimulus files should be represented
  together without renaming or losing provenance.
