# CND 1.0 specification audit

Audit performed on 26 August 2026 against the official five-page CND
Specifications document (version 1.0, last updated 24 January 2024).

## Structural requirements checked

| Specification rule | Converter behavior | Evidence |
| --- | --- | --- |
| `dataSub*.mat` contains one variable per recording modality | Lists every structure with `data` and `fs`; caller can select one with `neural_variable` | v5/v7.3 multimodal regression tests |
| Unselected modalities may include pupillometry, accelerometers, or MEG | Preserved as top-level `additional_variables` without pretending they are supported MNE channel types | MATLAB and template-backed MNE round-trip tests |
| Neural `data` is a `1 x N` cell array of time-by-channel trials | Normalized to a tuple of time-by-channel arrays and reconstructed on write | fixture, property, and catalogue tests |
| Stimulus `data` is an `M x N` feature-by-trial cell array | Preserved as feature -> trial arrays | fixture, property, and catalogue tests |
| Trials may have different lengths | One MNE `RawArray` is created per trial | variable-length tests and public catalogue |
| `origTrialPosition` retains presentation order | One-based stored values are preserved | round-trip tests |
| `chanlocs` uses a `1 x C` EEGLAB structure | Row-struct, columnar, and observed topomap variants are parsed; raw layout is retained | parser and real-dataset tests |
| Each `extChan` field can be a trial cell array for one external-signal type | Named fields are combined with retained names/counts and reconstructed | v5/v7.3 named-group tests |
| Neural and stimulus data correspond trial-by-trial | Trial counts, duration, and indices are validated | tolerant and strict validation tests |
| CND 1.0 expects equal neural/stimulus sampling rates | Warning in legacy mode and error in strict mode | AliceSpeech compatibility and validation tests |

## Compatibility policy

The public catalogue contains legacy files that do not satisfy every CND 1.0
recommendation. The normal reader therefore preserves the observed data and
reports conformance warnings. `strict_spec=True` turns specification deviations
that would be inappropriate in newly generated CND into errors. The converter
never repairs a sampling-rate mismatch, truncates a trial, guesses a physical
unit, or invents coordinate semantics.

MATLAB v5 preserves struct-field insertion order, whereas HDF5-backed v7.3
loading can expose fields lexicographically. Named `extChan` groups are sorted
by field name before their columns are combined. This produces stable channel
order across encodings while retaining each group boundary for reconstruction.

## Remaining semantic questions

The published structure does not define physical EEG/external-channel units,
coordinate units and frame, or an MNE representation for parallel naturalistic
stimulus features. Those are recorded in
[`questions-for-maintainers.md`](questions-for-maintainers.md) and cannot be
resolved safely by additional parser code.

## Source

- [CND Specifications PDF](https://data.cnspworkshop.net/CND_Specifications.pdf)
