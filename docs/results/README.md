# Verification results

`verify-dataset` on 24–25 August 2026, one subject at a time. Older JSON is schema 2. The current tool is schema 4. I did not rewrite the old files.

Each run: MATLAB opens, CND layout is valid, one MNE `Raw` per trial with matching numbers, stimulus views, a finite Welch PSD (empty files skip this), write-back through the original template.

For the 1,017 files with neural samples, numerical error was zero. That used a dummy unit of 1 (`V` in the JSON). **That does not mean the files are in volts.** Nobody wrote a unit down. Use the default (tolerant) reader for these old files. `--strict-spec` is for CND you just created.

[catalog-summary.json](catalog-summary.json): 1,026 neural files, 1,017 pass, 8 empty, 1 unreadable, 17,774 trials.

| Dataset | Subjects | Trials | Neural / stim | Channels | What stood out | Result | JSON |
| --- | ---: | ---: | --- | ---: | --- | --- | --- |
| Lalor Natural Speech | 19 | 380 | 128 / 128 Hz | 128 | variable trial lengths; seven neural trials unusually long | pass, warnings | [JSON](lalor-natural-speech.json) |
| AliceSpeech | 20 | 240 | 500 / 50 Hz | 60 | no channel names/locations; 10:1 rate mismatch | pass, tolerant | [JSON](alice-speech.json) |
| AAD KULeuven | 16 | 128 | 32 / 32 Hz | 64 | per-person stim; no `stimIdxs`; string conditions | pass | [JSON](aad-kuleuven.json) |
| Music Imagery | 21 | 1,848 | 64 / 64 Hz | 64 | `dataType` is a MATLAB string object | pass | [JSON](music-imagery.json) |
| Lalor Reversed Speech | 10 | 200 | 128 / 128 Hz | 128 | same kind of duration mismatch as Lalor | pass, warnings | [JSON](lalor-reversed-speech.json) |
| SparrKULee2 | 56 | 212 | 64 / 64 Hz | 64 | v7.3; mastoids; 0-byte `dataSub33.mat` skipped | pass | [JSON](sparr-kulee2.json) |
| Podcast fNIRS | 8 | 224 | 25 / 10 Hz | 48 | HbO/HbR/HbT grid, not one row of trials | pass | [JSON](podcast-fnirs.json) |
| ChildStories-Sysoeva | 52 | 148 | 500 / 500 Hz | 31 | labels in MATLAB MCOS strings | pass | [JSON](child-stories-sysoeva.json) |
| BabyRhythm adults | 68 files | 1,224 | 50 / 50 Hz | 58 | four preprocessing variants per person | pass | [JSON](baby-rhythm-adults.json) |
| BabyRhythm 4 months | 188 files | 3,368 | 50 / 50 Hz | 58 | 8 files have no neural samples | 180 pass | [JSON](baby-rhythm-4mo.json) |
| BabyRhythm 7 months | 188 files | 3,380 | 50 / 50 Hz | 58 | empty rejected trials kept | pass | [JSON](baby-rhythm-7mo.json) |
| BabyRhythm 11 months | 188 files | 3,384 | 50 / 50 Hz | 58 | empty rejected trials kept | pass | [JSON](baby-rhythm-11mo.json) |
| VocodedSpeech | 13 | 325 | 128 / 128 Hz | 128 | no subject 13; no channel locations | pass | [JSON](vocoded-speech.json) |
| FDSpeech L1 | 25 | 375 | 100 / 100 Hz | 64 | `pre_dataSubN.mat`; features often one sample off | pass | [JSON](fd-speech-l1.json) |
| FDSpeech L2 | 25 | 373 | 100 / 100 Hz | 64 | dropped `COMNT`/`SCALE` drawing helpers | pass | [JSON](fd-speech-l2.json) |
| PolyphonicBach | 31 | 993 | 500/125 or 250/125 Hz | 24 | sparse musical parts; one squeezed 1-sample trial | pass | [JSON](polyphonic-bach.json) |
| DiliBach | 20 | 600 | 512 / 64 Hz | 64 | empty `origTrialPosition`; big clock difference | pass | [JSON](dilibach.json) |
| SparrKULee1 | 78 files | 372 parsed | 64 Hz / no stim | 64 | `dataSub48.mat` truncated in the published zip | 77 pass | [JSON](sparr-kulee1.json) |

BabyRhythm is 632 CND files because each person has four preprocessing variants; the eight empty ones are 4-month participants 8 and 13, all four variants. VocodedSpeech jumps from 12 to 14. SparrKULee1 `dataSub48.mat` passes zip CRC but the HDF5 file is truncated ([manifest](../manifests/sparr-kulee1.json)). Zip checksums: [manifests](../manifests/README.md).
