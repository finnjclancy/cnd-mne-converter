"""Minimal, explicit CND -> MNE -> CND workflow.

Replace the paths and unit only after confirming the dataset's documentation.
"""

from pathlib import Path

from cnd_mne import read_cnd_mne

source = Path("/path/to/dataset/dataCND")
destination = Path("converted/dataCND")

recording = read_cnd_mne(source, subject=1, neural_unit="uV")
print(recording.raws[0])
print(recording.trial_metadata[0])

# Run ordinary MNE operations per trial. Keep trial lengths unchanged when a
# template-backed round trip is required.
for raw in recording.raws:
    if raw.n_times:
        raw.filter(1.0, 15.0)

recording.write_cnd(
    destination,
    subject=1,
    output_unit="uV",
    mat_version="7.3",
)
