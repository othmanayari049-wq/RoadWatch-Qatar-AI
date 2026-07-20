"""Application exceptions translated into stable API error responses."""


class RoadWatchError(Exception):
    """Base class for expected application failures."""


class InvalidImageError(RoadWatchError):
    """Raised when uploaded bytes are not a safe supported image."""


class ModelUnavailableError(RoadWatchError):
    """Raised when inference is requested without a usable trained model."""


class UnknownDamageClassError(RoadWatchError):
    """Raised when model metadata does not map to the RDD2022 class system."""

