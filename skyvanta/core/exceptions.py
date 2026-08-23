"""Custom exception hierarchy for SkyVanta AI."""


class SkyVantaError(Exception):
    """Base exception for all SkyVanta errors."""
    pass


class VideoSourceError(SkyVantaError):
    """Raised when video capture or stream cannot be opened."""
    pass


class ModelLoadError(SkyVantaError):
    """Raised when deep learning detector weights fail to load."""
    pass


class ConfigurationError(SkyVantaError):
    """Raised when configuration validation or file parsing fails."""
    pass
