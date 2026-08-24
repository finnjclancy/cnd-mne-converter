# Observed public dataset compatibility

The table below records a structural scan of every subject file in six public
archives. This is not scientific validation of the datasets or their physical
units.

| Dataset | Subjects scanned | Trials per subject | Neural / stimulus rate | Channels | Features | Important variation | Prototype result |
| --- | ---: | ---: | --- | ---: | ---: | --- | --- |
| LalorNatSpeech | 19 | 20 | 128 / 128 Hz | 128 | 4 | Channel locations, mastoids, multidimensional spectrogram and phonetic features; all trials differ in duration and seven neural trials are unusually long | Full MNE and round-trip matrix passes with explicit warnings |
| AliceSpeech | 20 | 12 | 500 / 50 Hz | 60 | 2 | No channel names or locations; a CND 1.0 sampling-rate mismatch and a 0.02 s duration difference | Full MNE and round-trip matrix passes in tolerant legacy mode |
| AAD KULeuven | 16 | 8 | 32 / 32 Hz | 64 | 1 per stimulus file | Subject-specific `stimCND/dataStimN.mat`; separate unattended envelope; missing `stimIdxs`; string conditions; rich subject fields | Full MNE and round-trip matrix passes; missing indices reported |
| MusicImagery | 21 | 88 | 64 / 64 Hz | 64 | 2 | Listening and imagery conditions; opaque MATLAB `string` object in `dataType` | Full MNE and round-trip matrix passes; modality safely inferred from top-level `eeg` variable |
| LalorRevSpeech | 10 | 20 | 128 / 128 Hz | 128 | 2 | Time-reversed speech, mastoids, channel locations, and large legacy duration differences | Full MNE and round-trip matrix passes with explicit warnings |
| SparrKULee2 | 56 non-empty | 1–5 | 64 / 64 Hz | 64 | 1 | MATLAB v7.3/HDF5; subject-specific stimulus files; two mastoid groups; one 0-byte subject placeholder in the official archive | All 56 usable subjects pass MNE and round-trip checks; placeholder is recorded and skipped |

All 142 non-empty subject files parsed without structural validation errors.
Across 3,008 trials, all neural and stimulus MNE views, Welch PSD smoke checks, and controlled
round trips passed with zero numerical error under the explicitly recorded `V`
identity-test assumption. This assumption tests software behavior; it is not a
scientific assertion about the source unit. See the [JSON evidence](results/README.md).

## Cross-dataset findings

1. None of the six inspected legacy datasets declares `cndVersion`.
2. None declares an unambiguous EEG physical unit.
3. CND 1.0 requires equal neural and stimulus sampling rates, but compatibility
   mode cannot enforce that rule because Alice stores them at a 10:1 ratio.
4. Sample-count truncation is not a general alignment solution.
5. Channel locations cannot be required because Alice omits them.
6. `stimIdxs` and numeric `condIdxs` cannot be assumed because AAD omits the
   former and uses string values for the latter.
7. Unknown neural fields matter. AAD contains attention ear, story, experiment,
   original sampling rate, and stimulus-track metadata.
8. MATLAB scalar strings are not uniform. MusicImagery contains an opaque MCOS
   string object for `dataType` even though ordinary strings are used elsewhere.
9. MATLAB storage versions are not uniform. SparrKULee2 requires HDF5 object
   references, reversed array axes, subject-specific stimuli, and nested
   external-channel groups.

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

Full public datasets remain outside Git history and are available as release
assets. The verifier loads each subject sequentially to bound memory use:

```bash
uv run cnd-mne verify-dataset /path/to/dataset \
  --neural-unit V \
  --output verification.json
```

Use `V` only for a neutral numerical identity test. A scientific run must use a
confirmed physical unit.

## Unresolved scientific questions

- Confirm stored EEG units for each public CND dataset with its documentation
  or data owner.
- Confirm coordinate unit and head-frame semantics for EEGLAB-style
  `chanlocs`.
- Define the meaning of neural samples before and after the stimulus, including
  datasets with and without `paddingStartSample`.
- Determine whether the seven unusually long Lalor neural trials across five
  subjects are intentional; their largest neural/stimulus difference is 197 s.
- Decide how attended and unattended AAD stimulus files should be represented
  together without renaming or losing provenance.
