# Public dataset compatibility

What the downloadable CND collections actually look like. This is a structural scan, not "the science is correct", and it does not assign units.

| Dataset | Subjects scanned | Trials per subject | Neural / stimulus rate | Channels | Features | What stood out | Result |
| --- | ---: | ---: | --- | ---: | ---: | --- | --- |
| LalorNatSpeech | 19 | 20 | 128 / 128 Hz | 128 | 4 | channel locations, mastoids, spectrograms; trial lengths vary; seven neural trials are unusually long | pass, with warnings |
| AliceSpeech | 20 | 12 | 500 / 50 Hz | 60 | 2 | no channel names or locations; 10:1 rate mismatch; 0.02 s duration drift | pass in tolerant mode |
| AAD KULeuven | 16 | 8 | 32 / 32 Hz | 64 | 1 per stimulus file | one stim file per person; unattended envelope; no `stimIdxs`; string conditions | pass; missing indices reported |
| MusicImagery | 21 | 88 | 64 / 64 Hz | 64 | 2 | listening vs imagery; `dataType` is a MATLAB string object | pass |
| LalorRevSpeech | 10 | 20 | 128 / 128 Hz | 128 | 2 | reversed speech; same kind of duration mismatch as Lalor | pass, with warnings |
| SparrKULee2 | 56 non-empty | 1–5 | 64 / 64 Hz | 64 | 1 | MATLAB v7.3; per-subject stim files; two mastoid groups; one 0-byte file in the zip | 56 usable subjects pass |
| Podcast fNIRS | 8 | 28 | 25 / 10 Hz | 48 (16 HbO, 16 HbR, 16 HbT) | 5 | 3×28 signal-type grid, not a simple trial row; windows longer than the stim tracks | pass; differences stay as warnings |
| ChildStories-Sysoeva | 52 | 2–3 | 500 / 500 Hz | 31 | 3 | named participant/stim pairs; labels stored as MATLAB MCOS strings | all 52 pass after decoding those labels |
| BabyRhythm | 632 files / 158 people | up to 18 | 50 / 50 Hz | 58 | 4 | four preprocessing variants per person; empty rejected trials kept | 624 pass; 8 files have no samples |
| VocodedSpeech | 13 | 25 | 128 / 128 Hz | 128 | 3 | no subject 13; no channel locations; per-subject stim | all 13 pass; numbering gap kept |
| FDSpeech L1 | 25 | 15 | 100 / 100 Hz | 64 | 12 | `pre_dataSubN.mat` names; features often one sample off | all 25 pass; 305 length warnings kept |
| FDSpeech L2 | 25 | 13–15 | 100 / 100 Hz | 64 | 12 | some files mix 64 EEG channels with `COMNT`/`SCALE` drawing helpers | all 25 pass after dropping the helpers |
| PolyphonicBach | 31 | 32 | 500 / 125 or 250 / 125 Hz | 24 | 48 | sparse left/right musical parts; one squeezed one-sample trial | all 31 pass |
| DiliBach | 20 | 30 | 512 / 64 Hz | 64 | 7 | empty `origTrialPosition`; pitch/onset features; big clock difference | all 20 pass |
| SparrKULee1 | 78 files | 1–11 | 64 Hz / no stim in the zip | 64 | 0 | v7.3; mastoids; subject 48 is a truncated HDF5 file | 77 pass; 48 is broken upstream |

1,017 of 1,026 neural files pass. Eight BabyRhythm files convert but have no samples. One SparrKULee1 file cannot be opened. Details: [results](results/README.md).

## Things that showed up more than once

- almost nobody wrote `cndVersion` or a physical unit
- Alice proves you cannot require matching neural/stimulus sample rates, or channel locations
- cutting samples to "fix" a length mismatch is a bad general rule
- AAD has no `stimIdxs` and uses strings for conditions, so those fields are optional
- extra MATLAB fields matter (attention ear, story, original rate, …). dropping unknowns would lose them
- MATLAB strings are messy: MusicImagery and ChildStories hide labels in MCOS objects
- some collections are v5, some are v7.3/HDF5 (SparrKULee2)
- Podcast fNIRS is a grid of signal types, not one row of trials. flatten it wrong and you get 84 fake trials
- BabyRhythm empty cells are rejected infant trials. keep the slot. eight 4-month files are empty all the way through
- FDSpeech features can be one sample longer/shorter than the EEG. warn, do not pad
- `chanlocs` is not always EEGLAB electrodes. FDSpeech L2 stuffed a 2D plot layout in there
- MATLAB will squeeze a 1×24 trial into a length-24 vector. PolyphonicBach subject 16 is one sample, 24 channels
- empty `origTrialPosition` in DiliBach means "not set", not a trial-order list of length 0
- a zip can pass CRC and still contain a truncated `.mat` (SparrKULee1 subject 48)

## How this was checked

Tiny fake MATLAB files in CI cover the awkward layouts (unequal trials, missing indices, extra channels, round trip).

The real zips are not in git. Locally:

```bash
uv run cnd-mne verify-dataset /path/to/dataset \
  --neural-unit V \
  --output verification.json
```

`V` here is only "multiply by one" so copy/orientation bugs show up. For science, use a unit the owner confirmed.

## Still unknown

- EEG units for each public dataset
- `chanlocs` units / frame
- what `paddingStartSample` is for
- whether Lalor's ~197 s extra neural time is on purpose (subjects 1, 3, 6, 7, 8)
- how attended and unattended AAD files should sit together
