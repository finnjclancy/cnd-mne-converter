# Verification results

I ran `verify-dataset` on 24–25 August 2026, one subject at a time. Older JSON files are schema 2. The current tool is schema 4 (it can also write MATLAB and read it back). I did not rewrite the old files to pretend those extra checks ran.

| Dataset | Subjects | Trials | Result | JSON |
| --- | ---: | ---: | --- | --- |
| Lalor Natural Speech | 19 | 380 | Pass, with the usual legacy warnings | [JSON](lalor-natural-speech.json) |
| AliceSpeech | 20 | 240 | Pass, with the usual legacy warnings | [JSON](alice-speech.json) |
| AAD KULeuven | 16 | 128 | Pass, with the usual legacy warnings | [JSON](aad-kuleuven.json) |
| Music Imagery | 21 | 1,848 | Pass, with the usual legacy warnings | [JSON](music-imagery.json) |
| Lalor Reversed Speech | 10 | 200 | Pass, with the usual legacy warnings | [JSON](lalor-reversed-speech.json) |
| SparrKULee2 | 56 | 212 | Pass. one 0-byte file in the zip was skipped | [JSON](sparr-kulee2.json) |
| Podcast fNIRS | 8 | 224 | Pass after teaching the reader the HbO/HbR/HbT grid | [JSON](podcast-fnirs.json) |
| ChildStories-Sysoeva | 52 | 148 | Pass after decoding MATLAB string objects | [JSON](child-stories-sysoeva.json) |
| BabyRhythm adults | 68 CND files | 1,224 | Pass | [JSON](baby-rhythm-adults.json) |
| BabyRhythm 4 months | 188 CND files | 3,368 | 180 pass. 8 files have no neural samples | [JSON](baby-rhythm-4mo.json) |
| BabyRhythm 7 months | 188 CND files | 3,380 | Pass. empty rejected trials are kept | [JSON](baby-rhythm-7mo.json) |
| BabyRhythm 11 months | 188 CND files | 3,384 | Pass. empty rejected trials are kept | [JSON](baby-rhythm-11mo.json) |
| VocodedSpeech | 13 | 325 | Pass | [JSON](vocoded-speech.json) |
| FDSpeech L1 | 25 | 375 | Pass. some features are one sample off | [JSON](fd-speech-l1.json) |
| FDSpeech L2 | 25 | 373 | Pass after ignoring `COMNT`/`SCALE` drawing helpers | [JSON](fd-speech-l2.json) |
| PolyphonicBach | 31 | 993 | Pass. sparse musical parts stay empty | [JSON](polyphonic-bach.json) |
| DiliBach | 20 | 600 | Pass. empty `origTrialPosition` treated as missing | [JSON](dilibach.json) |
| SparrKULee1 | 78 files | 372 parsed | 77 pass. `dataSub48.mat` is truncated in the published zip | [JSON](sparr-kulee1.json) |

Added up in [catalog-summary.json](catalog-summary.json): 1,026 neural files, 1,017 pass, 8 empty, 1 unreadable, 17,774 trials.

SparrKULee2's zip has 57 matching names. `dataSub33.mat` is 0 bytes, so the catalogue's 56 usable people is right. That placeholder is not one of the 1,026 non-empty files.

## What each run checked

- MATLAB opens and the CND layout is valid
- one MNE `Raw` per neural trial, values and orientation match
- stimulus tracks as MNE views
- a finite Welch PSD (needs some samples, so empty files skip this)
- write back through the original CND template; leftover fields survive

For the 1,017 files with neural samples, the numerical error was zero. That used a dummy unit of 1 (`V` in the JSON). **That does not mean the files are in volts.** Nobody wrote a unit down. Empty files still round-trip; they just have nothing to plot.

## Weird files, not converter bugs

- BabyRhythm counts 632 CND files because each person has four preprocessing variants. Eight of those (4-month participants 8 and 13, all four variants) have zero neural samples.
- VocodedSpeech has no subject 13. The zip jumps to 14.
- SparrKULee1 `dataSub48.mat`: the zip and the entry both pass CRC, but the HDF5 file ends before it says it should. Hashes are in the [manifest](../manifests/sparr-kulee1.json).

## Warnings I kept on purpose

- almost every file omits `cndVersion` and a neural unit
- AliceSpeech is 500 Hz EEG / 50 Hz stimulus, plus 0.02 s duration drift, and no channel locations
- AAD KULeuven has no `stimIdxs`
- Lalor: every trial's neural and stimulus lengths differ. Five subjects have a few very long neural trials (up to 197 s extra)
- SparrKULee2: mastoids are a different length from the EEG. 89 pairs also have duration warnings

Use the default (tolerant) reader for these old files. Use `--strict-spec` when you are checking CND you just created.
