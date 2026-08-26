# Technical readiness before scientific review

## Bottom line

The standalone converter is technically ready for supervisor and maintainer
review. The remaining blockers are not unfinished parser work: they are
scientific semantics that are absent from legacy CND files and API choices that
must be agreed with the CND and MNE maintainers.

## Engineering completed

- Read and write MATLAB v5 and v7.3/HDF5 CND files.
- Preserve variable-length and empty trials, independent stimulus clocks,
  conditions, original trial positions, external data, and extension fields.
- Convert supported EEG and observed fNIRS layouts into MNE objects using
  explicit physical units.
- Provide continuous stimulus views, opt-in event annotations, external-channel
  views, and boundary-protected concatenation.
- Export edited MNE values using the retained CND template.
- Publish neural and stimulus files as one transactional output set: failed
  serialization or publication restores the previous files.
- Verify neural, stimulus, and external-channel values independently.
- Optionally exercise the actual MATLAB writer and reader during dataset
  verification for both supported MAT formats.
- Test Linux, macOS, Windows, Python 3.10–3.13, and minimum/current MNE.
- Build and install-test both the wheel and source distribution in CI.
- Record reproducible evidence for the full linked public CND catalogue.

## Checks completed locally

As of 26 August 2026:

- 110 automated tests pass;
- statement coverage is 96.23%;
- Ruff lint and format checks pass;
- Mypy passes for the typed public package, which includes a `py.typed` marker;
- the installed dependency set passes `uv pip check`;
- MATLAB v5 and v7.3 serialized round trips pass on the committed fixture; and
- the repository has no known converter defect among readable public files.

## Decisions that cannot be made safely in code

1. The physical EEG unit of each legacy public dataset.
2. The unit, axes, origin, and frame of CND channel coordinates.
3. The intended meaning of `paddingStartSample` and surplus samples.
4. Which external channels represent EEG references, EOG, audio, triggers, or
   other measurements, and their units.
5. Which sparse stimulus features should be treated as events.
6. Whether the proposed companion object is the API MNE wants upstream.
7. Whether the first upstream scope is import only, import/export, or also TRF
   results.

The converter deliberately exposes these as explicit arguments or retained
metadata instead of inserting undocumented defaults.

## Work after answers are received

Once a reference dataset and its semantics are confirmed, the remaining work
is a bounded validation and upstreaming exercise:

1. run the independent scientific comparison;
2. record the approved unit and coordinate policy;
3. adjust the public API if maintainers request it;
4. prepare review-sized MNE contributions; and
5. tag the first release after approval.

MEG, arbitrary fNIRS layouts, lazy loading, automatic alignment/resampling, and
TRF-result interchange are intentionally excluded from the first scope. They
require real examples or scientific/API decisions and should not be presented
as generic transformations that are safe to implement speculatively.
