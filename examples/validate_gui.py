"""Reproduce the real-data numerical checks used by the desktop GUI audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import mne
import numpy as np
from mne.viz.topomap import _prepare_topomap_plot

from cnd_mne import read_cnd, read_cnd_mne
from cnd_mne.gui import CNDImporterApp


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument(
    "dataset",
    type=Path,
    help="Lalor sample directory containing pre_dataSub1.mat and dataStim.mat",
)
parser.add_argument(
    "--output",
    type=Path,
    default=Path("docs/results/giovanni-review/gui-audit.json"),
)
args = parser.parse_args()
dataset = args.dataset.resolve()

cnd = read_cnd(dataset, subject=1)
converted = read_cnd_mne(
    dataset,
    subject=1,
    neural_unit="uV",
    montage="eeglab",
    coordinate_scale_to_meters=0.095,
)
raw = converted.raws[0]
display, montage_name = CNDImporterApp._display_raw(raw)
sphere = CNDImporterApp._topomap_sphere(display)
topomap_positions = _prepare_topomap_plot(display.info, "eeg", sphere=sphere)[1]

display_positions = display.get_montage().get_positions()["ch_pos"]
display_origin = np.asarray(sphere[:3])
angular_errors = []
source_locations = {
    str(location["labels"]): np.asarray(
        [-location["Y"], location["X"], location["Z"]], dtype=float
    )
    for location in cnd.neural.channel_locations or ()
}
for name in raw.ch_names:
    source_direction = source_locations[name] / np.linalg.norm(source_locations[name])
    display_direction = display_positions[name] - display_origin
    display_direction /= np.linalg.norm(display_direction)
    angular_errors.append(
        np.degrees(
            np.arccos(np.clip(float(source_direction @ display_direction), -1.0, 1.0))
        )
    )

conversion_errors = []
all_data_finite = True
all_psds_finite = True
total_samples = 0
for source_trial, trial_raw in zip(cnd.neural.trials, converted.raws, strict=True):
    expected_volts = np.asarray(source_trial, dtype=np.float64).T * 1e-6
    conversion_errors.append(
        float(np.max(np.abs(trial_raw.get_data() - expected_volts)))
    )
    all_data_finite &= bool(np.isfinite(trial_raw.get_data()).all())
    all_psds_finite &= bool(
        np.isfinite(trial_raw.compute_psd(verbose=False).get_data()).all()
    )
    total_samples += trial_raw.n_times
source_radii = [np.linalg.norm(position) for position in source_locations.values()]
report = {
    "mne_version": mne.__version__,
    "numpy_version": np.__version__,
    "dataset": str(dataset),
    "source_sha256": {
        path.name: _sha256(path)
        for path in sorted(dataset.glob("*.mat"))
        if path.name in {"pre_dataSub1.mat", "dataStim.mat"}
    },
    "trials": len(converted.raws),
    "channels": len(raw.ch_names),
    "total_samples_per_channel": int(total_samples),
    "sampling_frequency_hz": raw.info["sfreq"],
    "source_unit_declared": cnd.neural.data_unit,
    "gui_unit_input": "uV",
    "unit_status": "plotting assumption; source CND does not declare a physical unit",
    "source_coordinate_median_radius": float(np.median(source_radii)),
    "coordinate_scale_to_meters": 0.095,
    "source_to_mne_volts_max_abs_error_all_trials": max(conversion_errors),
    "all_mne_data_finite": all_data_finite,
    "display_copy_data_max_abs_error": float(
        np.max(np.abs(display.get_data() - raw.get_data()))
    ),
    "biosemi_montage_match": montage_name,
    "channel_order_unchanged": display.ch_names == raw.ch_names,
    "max_source_vs_display_direction_error_degrees": float(max(angular_errors)),
    "topomap_sphere_m": list(sphere),
    "max_projected_sensor_radius_m": float(
        np.linalg.norm(topomap_positions, axis=1).max()
    ),
    "all_sensors_inside_topomap_outline": bool(
        np.linalg.norm(topomap_positions, axis=1).max() <= sphere[3]
    ),
    "all_power_spectra_finite": all_psds_finite,
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, indent=2) + "\n")
print(args.output)
