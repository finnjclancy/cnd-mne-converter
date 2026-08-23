# ADR 0001: Use a canonical CND model between file I/O and MNE

- Status: Accepted
- Date: 2026-08-22

## Context

CND stores synchronized neural trials, stimulus feature sets, presentation
order, conditions, channel information, and extensible MATLAB fields. MNE's
core objects represent neurophysiological recordings well, but a bare `Raw`
object is not a complete representation of all CND stimulus and trial metadata.

Implementing direct CND-to-MNE and MNE-to-CND functions independently would
duplicate mapping rules and make round-trip guarantees difficult to test.

## Decision

Introduce a canonical in-memory CND model. File readers and writers translate
between MATLAB and this model. An MNE adapter translates between the model and
MNE objects.

The model should contain:

- neural trials;
- channel and acquisition metadata;
- stimulus feature sets;
- condition and trial-order metadata;
- CND version information; and
- unrecognized additional fields needed for round-trip preservation.

The first implementation uses `CNDRecording`, `CNDNeural`, and `CNDStimulus`
dataclasses. Numerical arrays retain CND's native orientation and values until
an adapter performs an explicitly parameterized transformation.

## Consequences

### Benefits

- One source of truth for mapping and validation.
- CND-specific information survives while users work with MNE objects.
- Round-trip tests can isolate file parsing from MNE conversion.
- Future adapters can reuse the same model.

### Costs

- The package exposes a container in addition to native MNE objects.
- Arbitrary MNE-to-CND conversion still requires stimulus and trial information
  that cannot be inferred from neural data alone.
- The model requires a clearly documented stability policy.
