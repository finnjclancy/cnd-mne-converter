# Changelog

All notable changes are documented here. The project follows semantic
versioning once it reaches its first tagged release.

## Unreleased

### Added

- Bidirectional CND and MNE conversion for EEG and observed fNIRS layouts.
- MATLAB v5 and v7.3/HDF5 reading and transactional writing.
- Direct `read_cnd_mne()` and `MNECNDRecording.write_cnd()` APIs.
- Explicit MNE views for external channels and sparse stimulus annotations.
- Tolerant legacy and strict CND 1.0 validation.
- Full public-catalogue verification and machine-readable evidence.
- Optional on-disk MATLAB v5/v7.3 verification and external-channel view checks.
- Transactional publication and rollback for neural/stimulus output pairs.
- Wheel and source-distribution installation smoke tests in CI.
- PEP 561 typing marker and a passing Mypy CI check.

### Changed

- Verification schema 4 adds explicit serialized-round-trip evidence. The
  outcome model distinguishes complete passes, structurally valid
  zero-neural-data files, validation failures, conversion failures, and source
  read failures.

## 0.1.0.dev0 - 2026-08-25

- Initial research prototype and public-catalogue interoperability milestone.
