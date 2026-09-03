# Tests

Coverage only means "did this line run". It is not "percent of datasets supported" and it is not scientific correctness.

116 tests, 95.34% coverage. The rest is mostly defensive branches. CI fails if coverage drops below 95%. Add tests for new behaviour; do not farm coverage by mocking the public API away.

## What the suite actually covers

**Fast CI** — valid and broken MATLAB, units, montages, variable-length trials, stimulus views, atomic writes, CLI, round trips. Linux / macOS / Windows, Python 3.10–3.13, oldest and newest supported MNE. SciPy is capped below 1.17 while MNE 1.8 is still supported (that MNE release uses a SciPy API that 1.17 removed).

**Committed fixtures** — small `.mat` and `.fif` files, plus install-testing the wheel and sdist. Mypy on the public API.

**Public datasets** — `verify-dataset` locally, not in git. Parse, validate, build MNE, compare numbers, stimulus views, a Welch PSD, write back through the original CND. `--serialized-round-trip` also hits the real MATLAB writer. JSON is in [results](../results/README.md).

## Still needs a human

Units, coordinates, padding, extra-channel types, MATLAB independently opening our v7.3 files, MEG, TRF files, and whether this API is what MNE wants. 100% coverage would not answer those.
