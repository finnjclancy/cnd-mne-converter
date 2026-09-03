# Why there is an in-memory CND model

Accepted 22 August 2026.

CND has trials, stimulus tracks, presentation order, conditions, channels, and leftover MATLAB fields. A bare MNE `Raw` cannot hold all of that. If CND→MNE and MNE→CND each had their own mapping, round trips would be a mess to test.

So: MATLAB ↔ `CNDRecording` / `CNDNeural` / `CNDStimulus` ↔ MNE. Arrays stay in CND orientation until you ask for a conversion (unit, montage, …).

Cost: the package exposes a container, not only MNE objects. A random `Raw` still cannot invent envelopes.
