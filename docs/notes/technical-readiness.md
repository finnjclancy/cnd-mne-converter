# Technical readiness

The parser/writer is in good enough shape for review. What is left is not "handle one more MATLAB layout". It is units, coordinates, padding, and whether this API is what MNE would even want.

## Done

- Read and write MATLAB v5 and v7.3
- Keep variable-length trials, leftover modalities, extra channels, unknown fields
- EEG + the public-catalogue fNIRS layout, with explicit units
- Stimulus views, optional event annotations, optional concatenation
- Write back through the original CND template
- `verify-dataset` on the public catalogue (see [results](../results/README.md))
- CI on Linux / macOS / Windows, Python 3.10–3.13

As of 26 August 2026: 116 tests, 95% statement coverage, ruff + mypy clean. NAPlib and Eelbrain can load the committed fixture (Eelbrain needs two layouts stripped; its reader is narrower).

## Will not be decided in code

1. Physical EEG unit of each legacy dataset
2. `chanlocs` units / axes / frame
3. `paddingStartSample` and surplus samples
4. What extra channels actually are
5. Which sparse features are events
6. Whether the companion object is the upstream MNE API
7. Import-only vs import+export vs TRF files

## After those answers

Pick one subject, compare against MATLAB / NAPlib / Eelbrain, write down the unit and coordinate policy, then a small MNE proposal. MEG, lazy loading, auto-alignment, and TRF interchange stay out of that first proposal.
