# Changelog

Nothing is tagged as a real release yet. This is what is on `main`.

## Unreleased

- Read and write CND for EEG and the public-catalogue fNIRS layout
- MATLAB v5 and v7.3
- `read_cnd_mne()` and `write_cnd()`
- Optional views for extra sensors and sparse events
- Tolerant mode for old files, `--strict-spec` for new CND
- Ran `verify-dataset` on the public catalogue (JSON in `docs/results/`)
- Optional on-disk MATLAB round trip
- Writes are transactional (neural + stim together, or neither)
- CI: tests, ruff, mypy, wheel/sdist install, locked-dependency audit
- More than one recording type in one subject file: pick one, keep the rest
- Named `extChan.<type>` groups, same channel order in v5 and v7.3
- Dependabot for Python and Actions
- Jupyter is in the `dev` extra so the walkthrough notebook opens after `uv sync --extra dev`
- Shorter public-API docstrings

Verifier schema 4 can record an on-disk MATLAB round trip. Old JSON reports were not rewritten.

## 0.1.0.dev0 - 2026-08-25

First prototype that could open the public catalogue files.
