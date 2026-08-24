"""Bidirectional conversion between CND and MNE-Python."""

from .exceptions import (
    CNDAmbiguousUnitError,
    CNDError,
    CNDReadError,
    CNDUnsupportedError,
    CNDValidationError,
)
from .inspection import inspect_cnd
from .io import read_cnd, read_cnd_neural, read_cnd_stimulus, write_cnd
from .mne import MNECNDRecording, from_mne, to_mne
from .model import CNDNeural, CNDPaths, CNDRecording, CNDStimulus, CNDTrialMetadata
from .validation import ValidationIssue, ValidationReport, validate_cnd
from .verification import DatasetVerification, SubjectVerification, verify_dataset

__all__ = [
    "CNDAmbiguousUnitError",
    "CNDError",
    "CNDNeural",
    "CNDPaths",
    "CNDReadError",
    "CNDRecording",
    "CNDStimulus",
    "CNDTrialMetadata",
    "CNDUnsupportedError",
    "CNDValidationError",
    "DatasetVerification",
    "MNECNDRecording",
    "SubjectVerification",
    "ValidationIssue",
    "ValidationReport",
    "from_mne",
    "inspect_cnd",
    "read_cnd",
    "read_cnd_neural",
    "read_cnd_stimulus",
    "to_mne",
    "validate_cnd",
    "verify_dataset",
    "write_cnd",
]

__version__ = "0.1.0.dev0"
