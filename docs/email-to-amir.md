# Draft email to Amir

**Subject:** CND–MNE converter: progress, test results and decisions needed

Hi Amir,

I wanted to give you a clear update on the CND–MNE converter before I take the
next step with it.

## What is working

I have built a Python converter that reads CND MATLAB files into a loss-aware
Python model and creates MNE objects without flattening or silently changing
the experiment structure. It currently supports:

- MATLAB v5 and v7.3/HDF5 CND files;
- EEG and the fNIRS layout found in the public CND catalogue;
- variable-length trials as separate MNE `Raw` objects;
- continuous stimulus features, sparse event annotations and external-channel
  views;
- controlled MNE-to-CND export, including v5 and v7.3 output; and
- tolerant checks for older datasets alongside strict CND 1.0 validation.

The code, tests and design notes are here:
https://github.com/finnjclancy/cnd-mne-converter

The automated suite currently has 104 passing tests with 96.8% statement
coverage. CI checks Linux, macOS, Windows and the supported MNE range.

## Public-dataset testing

I tested every downloadable CND collection linked from the public catalogue:
1,026 neural files across 18 report groups, covering 17,774 trials and roughly
11.3 billion scalar neural values.

Of these, 1,017 files passed parsing, MNE construction, numerical comparison,
an MNE power-spectrum check and a controlled CND round trip. Eight additional
files converted and round-tripped correctly but contained no neural samples.
One SparrKULee1 file is physically truncated in the published archive and is
the only source file that could not be read.

The detailed machine-readable results and limitations are committed in the
repository.

## What the tests establish

The tests give strong evidence that the converter preserves array orientation,
sample values, trial boundaries, stimulus clocks and CND-only metadata for the
public layouts examined.

They do not yet prove that the legacy datasets are scientifically scaled
correctly in MNE. Most of the public files do not declare their EEG unit or the
unit and frame of their electrode coordinates, so I have deliberately avoided
guessing either.

## Questions I need help resolving

### Data units

Do we know the stored EEG unit for the public CND datasets? If the answer
differs by dataset, is there a reliable source I should use for each one?

### Electrode coordinates

What units, axes and coordinate frame are intended for CND `chanlocs`? I can
apply the common EEGLAB-to-MNE axis transform, but only when the coordinate
scale is supplied explicitly.

### MNE API design

CND can contain separate variable-length trials and stimulus features with a
different sampling rate. My current design returns a small companion object
containing one MNE `Raw` per trial and retains the full CND model for export.
Does that seem like the right proposal to bring to the MNE maintainers, or
would you prefer a different representation?

### Independent scientific check

Could we choose one reference dataset and subject for an independent comparison
against the original MATLAB, NAPlib or Eelbrain workflow? Ideally, I would like
someone familiar with that experiment to confirm the units, montage, trial
alignment and resulting plots.

### Project scope

Should the first contribution focus on EEG recording import/export only, with
MEG, resampling and TRF results treated as separate later pieces?

## Proposed next step

My suggestion is to validate one known dataset scientifically, write up the
proposed public API, and then open a design discussion with the MNE maintainers
before trying to merge anything upstream.

Would you be available to review this with me, and should Giovanni be included
in that discussion from the start?

Thanks,

Finn
