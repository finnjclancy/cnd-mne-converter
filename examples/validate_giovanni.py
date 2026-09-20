"""Reproduce labelled sensor plots and MNE operations on local real fixtures.

The 95 mm radius is a plotting convention, not inferred physical head size.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne
import numpy as np
import xlrd

from cnd_mne import read_cnd, to_mne

parser = argparse.ArgumentParser()
parser.add_argument("--root", type=Path, required=True)
root = parser.parse_args().root.resolve()
out = root / "cnd-mne-converter/docs/results/giovanni-review"
out.mkdir(parents=True, exist_ok=True)
r = read_cnd(root / "tmp/cnd/lalor-pilot/pre_dataSub1.mat")
raw = to_mne(
    r, neural_unit="uV", montage="eeglab", coordinate_scale_to_meters=0.095
).raws[0]
workbook_path = root / "tmp/Cap_coords_all.xls"
sheet = xlrd.open_workbook(workbook_path).sheet_by_name("128-chan")
factory_positions = {}
for row in range(sheet.nrows):
    match = re.match(r"^([ABCD]\d+)\b", str(sheet.cell_value(row, 0)))
    if match:
        xyz = np.asarray(sheet.row_values(row)[4:7], dtype=float)
        factory_positions[match.group(1)] = xyz / np.linalg.norm(xyz) * 0.095
assert len(factory_positions) == 128
reference = mne.channels.make_dig_montage(ch_pos=factory_positions, coord_frame="head")
positions = raw.get_montage().get_positions()["ch_pos"]
ref = reference.get_positions()["ch_pos"]
errors = {}
for name, position in positions.items():
    u = position / np.linalg.norm(position)
    v = ref[name] / np.linalg.norm(ref[name])
    errors[name] = float(np.degrees(np.arccos(np.clip(u @ v, -1, 1))))
fig, axes = plt.subplots(1, 2, figsize=(20, 10))
raw.plot_sensors(show_names=True, axes=axes[0], show=False, sphere=0.095)
refraw = mne.io.RawArray(
    np.zeros((128, 2)), mne.create_info(reference.ch_names, 64, "eeg"), verbose=False
)
refraw.set_montage(mne.channels.make_dig_montage(ch_pos=ref, coord_frame="head"))
refraw.plot_sensors(show_names=True, axes=axes[1], show=False, sphere=0.095)
axes[0].set_title("Lalor CND → MNE: channel names preserved")
axes[1].set_title("BioSemi manufacturer 128-channel coordinates")
fig.savefig(out / "biosemi128-layout.png", dpi=150)
plt.close(fig)
p3 = root / "tmp/giovanni-validation/sub-001_task-P3/dataCND"
r = read_cnd(p3 / "dataSub1.mat", stimulus_path=p3 / "dataStim.mat")
raw = to_mne(r, neural_unit="V", montage="eeglab", coordinate_scale_to_meters=1).raws[0]
fig = raw.plot_sensors(show_names=True, show=False)
fig.savefig(out / "p3-sensors.png", dpi=150)
plt.close(fig)
segment = raw.copy().crop(tmax=30).filter(1, 40, verbose=False)
fig = segment.compute_psd(fmin=1, fmax=40, verbose=False).plot(
    show=False, spatial_colors=False
)
fig.savefig(out / "p3-psd.png", dpi=150)
plt.close(fig)
fig, ax = plt.subplots(figsize=(12, 4))
ax.plot(segment.times[:2048], segment.get_data(picks=["Cz"])[0, :2048] * 1e6)
ax.set(
    xlabel="Time (s)",
    ylabel="Cz (µV)",
    title="Converted ERP CORE P3: MNE 1–40 Hz filter",
)
fig.tight_layout()
fig.savefig(out / "p3-filtered.png", dpi=150)
plt.close(fig)
report = {
    "reference": "https://www.biosemi.com/download/Cap_coords_all.xls",
    "reference_sha256": hashlib.sha256(workbook_path.read_bytes()).hexdigest(),
    "reference_sheet": "128-chan",
    "coordinate_comparison": "Unit-vector directions; physical scale not validated",
    "max_angular_difference_degrees": max(errors.values()),
    "median_angular_difference_degrees": float(np.median(list(errors.values()))),
    "channel_angular_differences_degrees": errors,
    "p3_channels": len(raw.ch_names),
    "p3_filter_psd_finite": bool(np.isfinite(segment.get_data()).all()),
}
(out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
print(out)
