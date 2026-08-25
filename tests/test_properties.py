from __future__ import annotations

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from cnd_mne import CNDNeural, CNDRecording, to_mne


@settings(max_examples=40, deadline=None)
@given(
    data=st.data(),
    unit=st.sampled_from(("V", "mV", "uV", "nV")),
    n_trials=st.integers(1, 4),
    n_channels=st.integers(1, 6),
)
def test_variable_shape_unit_round_trip_is_numerically_stable(
    data, unit, n_trials, n_channels
) -> None:
    samples = data.draw(
        st.lists(st.integers(1, 30), min_size=n_trials, max_size=n_trials),
        label="samples",
    )
    finite_values = st.floats(
        min_value=-1e6,
        max_value=1e6,
        allow_nan=False,
        allow_infinity=False,
        width=64,
    )
    trials = tuple(
        data.draw(
            arrays(np.float64, (n_samples, n_channels), elements=finite_values),
            label=f"trial_{index}",
        )
        for index, n_samples in enumerate(samples)
    )
    locations = tuple({"labels": f"C{index}"} for index in range(1, n_channels + 1))
    source = CNDRecording(
        neural=CNDNeural(
            trials=trials,
            sfreq=128.0,
            channel_locations=locations,
            data_unit=unit,
        )
    )

    converted = to_mne(source)
    restored = converted.to_cnd(on_unsupported_metadata="raise")

    assert restored.neural.data_unit == unit
    assert [raw.n_times for raw in converted.raws] == samples
    for expected, actual in zip(trials, restored.neural.trials, strict=True):
        np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)
