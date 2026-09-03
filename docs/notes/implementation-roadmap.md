# Roadmap

Parser/writer for the public catalogue is done. See the [readme](../../README.md) and [results](../results/README.md).

## Waiting on the lab

Units, `chanlocs`, padding, extra channels, attended/unattended pairing, empty trials, and whether the companion-object API is what MNE would want. Listed in [questions-for-maintainers.md](../questions-for-maintainers.md).

Do not add silent defaults for those.

## After that

One gold-standard subject, compare against MATLAB / NAPlib / Eelbrain, then a small MNE proposal (import first).

## Later, not now

- MEG (need real CND examples)
- Resampling / alignment as an explicit derived step
- TRF result files
- Lazy loading of huge files
- Whatever MATLAB layouts show up outside the current catalogue
