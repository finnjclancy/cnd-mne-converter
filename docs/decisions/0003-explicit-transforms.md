# ADR 0003: Require explicit units, coordinate scaling, and resampling

- Status: Accepted
- Date: 2026-08-23

## Context

MNE stores EEG values in volts and sensor coordinates in metres. The inspected
legacy CND datasets do not declare EEG units or coordinate units consistently.
Some datasets also store neural and stimulus signals at different sampling
frequencies.

A wrong unit conversion can change EEG amplitudes by a factor of one million.
A wrong coordinate scale or axis mapping can produce plausible-looking but
incorrect topographies. Truncating arrays by sample count is invalid when their
sampling frequencies differ.

## Decision

- CND numerical values stay unchanged in the canonical model.
- CND-to-MNE conversion requires a declared or caller-supplied EEG unit.
- MNE montage creation is disabled by default. The initial EEGLAB-compatible
  axis transform requires an explicit multiplier to metres.
- Neural and stimulus durations are compared in seconds.
- The prototype never automatically resamples, truncates, or pads signals.

## Consequences

The initial API is more cautious and requires user input for legacy datasets.
It prevents silent scientific transformations and makes unresolved metadata
visible to the validator and documentation.
