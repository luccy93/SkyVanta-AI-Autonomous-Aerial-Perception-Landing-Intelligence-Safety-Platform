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


class CalibrationError(SkyVantaError):
    """Raised when camera calibration is missing, invalid, or malformed."""
    pass


class DetectorError(SkyVantaError):
    """Raised when target or fiducial detector encounters an unrecoverable failure."""
    pass


class PnPSolverError(SkyVantaError):
    """Raised when Perspective-n-Point pose solving fails or produces non-finite values."""
    pass


class GeometryError(SkyVantaError):
    """Raised when marker or target geometry is degenerate, non-convex, or malformed."""
    pass


class TransformError(SkyVantaError):
    """Base exception for spatial transform and coordinate frame operations."""
    pass


class InvalidTransformError(TransformError):
    """Raised when an SE(3) matrix is non-orthonormal, singular, or non-finite."""
    pass


class TransformLookupError(TransformError):
    """Raised when a transform lookup between two frames fails."""
    pass


class DisconnectedFrameError(TransformLookupError):
    """Raised when no connected transform path exists between two frames in the frame graph."""
    pass


class FrameError(SkyVantaError):
    """Raised when coordinate frame identifiers or metadata are invalid or ambiguous."""
    pass


