from __future__ import annotations

import numpy as np

from cnd_mne import CNDNeural, CNDRecording, read_cnd, write_cnd


def test_single_neural_and_external_channels_survive_matlab_squeeze(
    tmp_path,
) -> None:
    recording = CNDRecording(
        neural=CNDNeural(
            trials=(np.arange(10, dtype=float)[:, np.newaxis],),
            sfreq=10.0,
            external_trials=(np.arange(10, dtype=float)[:, np.newaxis],),
            data_unit="V",
            cnd_version=1.0,
        )
    )

    write_cnd(recording, tmp_path)
    loaded = read_cnd(tmp_path, subject=1)

    assert loaded.neural.trials[0].shape == (10, 1)
    assert loaded.neural.external_trials[0].shape == (10, 1)
