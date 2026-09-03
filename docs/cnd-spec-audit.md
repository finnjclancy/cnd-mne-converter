# CND 1.0 audit

Checked 26 August 2026 against the five-page [CND 1.0 spec](https://data.cnspworkshop.net/CND_Specifications.pdf) (24 January 2024).

| Spec says | What this package does | How we know |
| --- | --- | --- |
| `dataSub*.mat` has one variable per recording type | lists every structure with `data` and `fs`; pick one with `neural_variable` | v5/v7.3 tests with extra modalities |
| unused types (pupils, accel, MEG, …) | kept on `additional_variables`, not faked as MNE channel types | round-trip tests |
| neural `data` is a 1×N cell of time×channel trials | stored that way, written that way | fixture + catalogue tests |
| stimulus `data` is features×trials | kept as feature → trial arrays | same |
| trials can be different lengths | one MNE `Raw` per trial | variable-length tests + public files |
| `origTrialPosition` is presentation order | stored one-based, as in the file | round trip |
| `chanlocs` is a 1×C EEGLAB struct | parses the shapes we have seen; keeps the raw layout | parser + real files |
| each `extChan` field is one extra-signal type | named groups combined, then split again on write | v5/v7.3 tests |
| neural and stimulus trials line up | counts, duration, indices checked | tolerant and strict validation |
| same sampling rate for neural and stimulus | warning in normal mode, error in strict mode | AliceSpeech is 500/50 Hz |

## Old files vs new files

A lot of the public catalogue would fail a strict reading of CND 1.0. The default reader keeps what is in the file and warns. `strict_spec=True` is for CND you just wrote.

The converter will not "fix" a rate mismatch, chop a trial, guess a unit, or invent electrode coordinates.

MATLAB v5 keeps struct field order. v7.3/HDF5 can come back alphabetical. Named `extChan` groups are therefore sorted by name before combining, so channel order is the same in both encodings.

## What the spec does not say

Units, coordinate frame, and how MNE should hold a speech envelope. Those are in [questions-for-maintainers.md](questions-for-maintainers.md). More parser code will not answer them.
