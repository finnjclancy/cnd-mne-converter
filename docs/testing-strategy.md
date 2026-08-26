# Testing strategy and coverage interpretation

## Why statement coverage is not 100%

Statement coverage answers one narrow question: *which Python statements ran
during the automated test suite?* It does not measure the percentage of CND
datasets supported, prove scientific correctness, or show that every possible
MATLAB representation has been observed.

The current suite has 116 passing tests and 95.34% statement coverage. The
remaining statements are principally defensive guards that follow earlier
validation, process-entry code, a filesystem race check, and fallback behavior
for an environment in which package metadata is unavailable. Forcing these
lines to execute by mocking away the public validation boundary would increase
the number without giving strong evidence about real CND-to-MNE conversion.

The CI threshold is 95%. This is deliberately a regression floor, not a claim
that 95% is sufficient on its own. New behavior should add tests, and coverage
must not fall below the floor.

## Evidence layers

### 1. Focused automated tests

The fast CI suite checks valid and malformed MATLAB structures, validation
rules, unit conversion, montage handling, variable-length trials, stimulus
feature views, unsupported MNE metadata, atomic output, CLI behavior, and
controlled CND-to-MNE-to-CND round trips. CI runs on Linux, macOS, and Windows;
Python 3.10, 3.11, 3.12, and 3.13; and both the minimum and latest compatible MNE
versions. The dependency range caps SciPy below 1.17 while MNE 1.8 remains
supported because that MNE release imports a SciPy API removed in 1.17.
Property-based tests also generate variable trial counts, lengths, channel
counts, values, and supported physical units to exercise numerical round trips.

### 2. Committed interoperability fixtures

Small `.mat` and MNE `.fif` fixtures exercise the real SciPy and MNE file and
object boundaries in CI. These catch behavior that tests of NumPy arrays alone
cannot. CI also installs and imports the built wheel and source distribution,
so a successful source-tree test is not mistaken for a usable package. Mypy
checks the typed package API and the distribution includes a PEP 561
`py.typed` marker.

### 3. Public-dataset verification

Multi-gigabyte public archives are checked locally with `verify-dataset`. For
every subject, this performs parsing, structural validation, MNE construction,
shape and numerical comparisons, stimulus-view checks, a finite Welch PSD, and
a template-backed numerical round trip. External-channel views are now also
checked without asserting an unknown physiological type or unit. For bounded
reference datasets, `--serialized-round-trip` additionally tests the actual v5
or v7.3 MATLAB writer and reader. Machine-readable JSON reports are
committed under [`docs/results`](results/README.md).

The large source archives remain outside Git history. This keeps normal clones
and CI practical; checksums and authoritative download links record exactly
which bytes were tested.

## What still requires evidence

- A confirmed physical EEG unit for each legacy public dataset.
- Confirmed coordinate units and coordinate-frame semantics.
- Independent MATLAB confirmation that generated v7.3 files load as intended;
  Python read/write round trips are automated.
- Maintainer-approved defaults for external channel types; explicit caller-
  supplied mappings are implemented.
- Padding-aware neural/stimulus alignment semantics.
- Broader modality support beyond EEG and the observed fNIRS layout, including
  MEG, and TRF-result interchange.
- An agreed public API reviewed by the CND and MNE maintainers.

These are scientific or interoperability questions. Reaching 100% statement
coverage would not resolve them.
