# Observed public dataset compatibility

The table below records a structural scan of every subject file in six public
archives, plus the linked Podcast fNIRS collection. This is not scientific
validation of the datasets or their physical units. The remaining catalogue
downloads are tracked in the full-catalogue verification work.

| Dataset | Subjects scanned | Trials per subject | Neural / stimulus rate | Channels | Features | Important variation | Prototype result |
| --- | ---: | ---: | --- | ---: | ---: | --- | --- |
| LalorNatSpeech | 19 | 20 | 128 / 128 Hz | 128 | 4 | Channel locations, mastoids, multidimensional spectrogram and phonetic features; all trials differ in duration and seven neural trials are unusually long | Full MNE and round-trip matrix passes with explicit warnings |
| AliceSpeech | 20 | 12 | 500 / 50 Hz | 60 | 2 | No channel names or locations; a CND 1.0 sampling-rate mismatch and a 0.02 s duration difference | Full MNE and round-trip matrix passes in tolerant legacy mode |
| AAD KULeuven | 16 | 8 | 32 / 32 Hz | 64 | 1 per stimulus file | Subject-specific `stimCND/dataStimN.mat`; separate unattended envelope; missing `stimIdxs`; string conditions; rich subject fields | Full MNE and round-trip matrix passes; missing indices reported |
| MusicImagery | 21 | 88 | 64 / 64 Hz | 64 | 2 | Listening and imagery conditions; opaque MATLAB `string` object in `dataType` | Full MNE and round-trip matrix passes; modality safely inferred from top-level `eeg` variable |
| LalorRevSpeech | 10 | 20 | 128 / 128 Hz | 128 | 2 | Time-reversed speech, mastoids, channel locations, and large legacy duration differences | Full MNE and round-trip matrix passes with explicit warnings |
| SparrKULee2 | 56 non-empty | 1–5 | 64 / 64 Hz | 64 | 1 | MATLAB v7.3/HDF5; subject-specific stimulus files; two mastoid groups; one 0-byte subject placeholder in the official archive | All 56 usable subjects pass MNE and round-trip checks; placeholder is recorded and skipped |
| Podcast fNIRS | 8 | 28 | 25 / 10 Hz | 48 (16 HbO, 16 HbR, 16 HbT) | 5 | Neural data is a 3 x 28 signal-type grid rather than a simple trial row; no channel locations; fixed neural windows exceed paired stimulus durations | Full MNE and template round-trip matrix passes after lossless block normalization; differences remain warnings |
| ChildStories-Sysoeva | 52 | 2–3 | 500 / 500 Hz | 31 | 3 | Named `dataParticipant_ID.mat` and `dataStim_ID.mat` pairs; feature and condition labels stored as opaque MATLAB MCOS strings | All 52 participants pass after decoding MCOS labels from the embedded workspace |
| BabyRhythm | 632 files / 158 participants | Up to 18 | 50 / 50 Hz | 58 | 4 | Four preprocessing variants per participant across adult, 4-, 7-, and 11-month cohorts; shared parent stimulus; retained rejected/empty trials | 624 files pass; 8 files for two 4-month participants contain no neural samples and are documented as unusable source files |

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
10. Modalities need layout-specific normalization. Podcast fNIRS stores HbO,
    HbR, and HbT as rows of a signal-type x trial cell grid. Flattening that
    grid incorrectly creates 84 trials; the reader now combines each column
    into one 48-channel trial and retains block boundaries for export.
11. Modern MATLAB strings can appear in otherwise v5 `.mat` files.
    ChildStories stores six scientific labels as opaque MCOS handles. The
    reader resolves their one-based metadata indices against the embedded
    UTF-16LE function workspace instead of exposing object IDs as labels.
12. Empty cells can encode rejected infant trials. In tolerant mode they are
    retained as zero-sample MNE trials, excluded from the PSD smoke-test choice,
    and reported as warnings; strict CND validation rejects them. Eight 4-month
    files (participants 8 and 13, four preprocessing variants each) contain no
    neural samples at all, so analysis is impossible without fabricating data.

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
