"""Bidirectional conversion between CND and MNE-Python."""

from .exceptions import (
    CNDAmbiguousUnitError,
    CNDError,
    CNDReadError,
    CNDUnsupportedError,
    CNDValidationError,
)
from .inspection import inspect_cnd
from .io import (
    available_neural_variables,
    read_cnd,
    read_cnd_neural,
    read_cnd_stimulus,
    write_cnd,
)
from .mne import MNECNDRecording, from_mne, read_cnd_mne, to_mne
from .model import (
    CNDNeural,
    CNDPaths,
    CNDRecording,
    CNDStimulus,
    CNDTrialMetadata,
    ExternalLayout,
)
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
    "ExternalLayout",
    "MNECNDRecording",
    "SubjectVerification",
    "ValidationIssue",
    "ValidationReport",
    "available_neural_variables",
    "from_mne",
    "inspect_cnd",
    "read_cnd",
    "read_cnd_neural",
    "read_cnd_mne",
    "read_cnd_stimulus",
    "to_mne",
    "validate_cnd",
    "verify_dataset",
    "write_cnd",
]

__version__ = "0.1.0.dev0"
