# Draft email to Amir

**To:** Amirhossein Chalehchaleh

**Cc:** Giovanni Di Liberto

**Subject:** CND–MNE converter: technical work completed and questions

Hi Amir,

I wanted to send you an update on the CND–MNE project Giovanni mentioned and
ask for your guidance on the scientific and API decisions.

## What I have completed

I have built a standalone Python package that imports CND data into MNE and
exports edited MNE data back to CND:

https://github.com/finnjclancy/cnd-mne-converter

It reads and writes MATLAB v5 and v7.3 files, preserves variable-length trials
and independent stimulus clocks, supports EEG and the fNIRS structure found in
the public catalogue, and provides explicit MNE views for stimulus features,
sparse events, and external channels. Export uses the retained CND structure so
that experiment metadata is not discarded.

The repository currently has 116 passing tests with 95.34% statement coverage.
CI covers Linux, macOS, Windows, Python 3.10–3.13, minimum/current MNE, and
installation of both built distributions. The verifier can also write and
reread both MATLAB formats rather than testing only the in-memory conversion.
I have also audited the implementation against the official CND 1.0 document,
added lossless handling for multiple modality variables and both external-
channel layouts, and run compatibility checks with the NAPlib and Eelbrain
readers. Dependency and source security scans are clean.

## Public data testing

I tested every downloadable CND collection linked from the public catalogue:
1,026 neural files across 18 report groups, containing 17,774 trials and about
11.3 billion scalar neural values.

Of those, 1,017 completed the parsing, MNE construction, numerical comparison,
stimulus checks, power-spectrum smoke test, and controlled round trip. Eight
BabyRhythm files converted correctly but contained no neural samples. One file
inside the published SparrKULee1 archive is physically truncated and is the
only unreadable source file.

## Questions

The remaining issues require experiment or maintainer knowledge rather than
more generic conversion code:

1. Could we choose one dataset and subject that you know well for an independent
   comparison with the original MATLAB, NAPlib, or Eelbrain workflow?
2. What physical EEG unit should be used for that dataset?
3. What units, axes, origin, and coordinate frame apply to its channel
   locations?
4. How should `paddingStartSample`, surplus samples, and any external channels
   be interpreted in that experiment?
5. Does the proposed API—one MNE `Raw` per variable-length trial, held in a
   companion object with the complete CND metadata—seem appropriate to bring to
   the MNE maintainers?
6. Should the first upstream proposal focus on EEG import, or include export as
   well? I have kept TRF-result interchange separate for now.

Once we have those answers, I can record the approved mapping, run the
scientific comparison, and turn the existing implementation into a focused MNE
proposal.

Would you have time for a short call to review it? I can prepare a demonstration
with whichever dataset you recommend.

Best,

Finn
