"""Package-specific exceptions."""


class CNDError(Exception):
    """Base class for CND conversion errors."""


class CNDReadError(CNDError):
    """Raised when a CND MATLAB file cannot be interpreted."""


class CNDValidationError(CNDError):
    """Raised when invalid CND data prevents a requested operation."""


class CNDAmbiguousUnitError(CNDValidationError):
    """Raised when physical units are required but unavailable."""


class CNDUnsupportedError(CNDError):
    """Raised for a valid CND concept that is not supported yet."""
