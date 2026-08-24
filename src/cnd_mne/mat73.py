"""Minimal MATLAB v7.3/HDF5 decoder for CND structures.

MATLAB stores array dimensions in reverse order in v7.3 files and represents
cells and many struct fields as HDF5 object references. This module decodes the
ordinary numeric, character, logical, cell, and struct values needed by CND.
Unknown MATLAB object classes remain numeric arrays so experiment-specific
fields are not silently discarded.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import h5py
import numpy as np


def is_mat73(path: Path) -> bool:
    """Return whether ``path`` contains an HDF5 payload."""
    return bool(h5py.is_hdf5(path))


def load_mat73(path: Path) -> dict[str, Any]:
    """Load public variables from one MATLAB v7.3 file."""
    with h5py.File(path, "r") as handle:
        return {
            key: _decode(value, handle)
            for key, value in handle.items()
            if not key.startswith("#")
        }


def _decode(value: h5py.Group | h5py.Dataset, handle: h5py.File) -> Any:
    if isinstance(value, h5py.Group):
        return {key: _decode(item, handle) for key, item in value.items()}

    matlab_class = _matlab_class(value)
    if value.attrs.get("MATLAB_empty") is not None:
        return np.empty(0)

    if h5py.check_dtype(ref=value.dtype) is not None:
        references = np.asarray(value[()])
        decoded = np.empty(references.shape, dtype=object)
        for index in np.ndindex(references.shape):
            reference = references[index]
            decoded[index] = _decode(handle[reference], handle) if reference else None
        return np.squeeze(_matlab_axes(decoded))

    array = _matlab_axes(np.asarray(value[()]))
    if matlab_class == "char":
        return "".join(chr(int(code)) for code in array.ravel() if int(code) != 0)
    if matlab_class == "logical":
        array = array.astype(bool, copy=False)
    if array.dtype.names and {"real", "imag"} <= set(array.dtype.names):
        array = array["real"] + 1j * array["imag"]
    return array.item() if array.size == 1 else np.squeeze(array)


def _matlab_axes(array: np.ndarray) -> np.ndarray:
    if array.ndim < 2:
        return array
    return array.transpose(tuple(reversed(range(array.ndim))))


def _matlab_class(value: h5py.Dataset) -> str | None:
    stored = value.attrs.get("MATLAB_class")
    if isinstance(stored, bytes):
        return stored.decode("ascii", errors="replace")
    if isinstance(stored, np.bytes_):
        return bytes(stored).decode("ascii", errors="replace")
    return str(stored) if stored is not None else None
