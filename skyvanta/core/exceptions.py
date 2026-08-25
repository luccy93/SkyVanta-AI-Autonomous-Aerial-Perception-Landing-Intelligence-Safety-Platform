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


class FusionError(SkyVantaError):
    """Base exception for ESEKF and sensor fusion operations."""
    pass


class NumericalDivergenceError(FusionError):
    """Raised when covariance or state estimation experiences numerical divergence or NaN/Inf."""
    pass


class GatingError(FusionError):
    """Raised when measurement innovation fails statistical gating checks."""
    pass


class InitializationError(FusionError):
    """Raised when ESEKF estimator initialization fails or receives invalid initial parameters."""
    pass


class SensorTimingError(FusionError):
    """Raised when sensor timestamp ordering, delta-t, or staleness violates timing constraints."""
    pass


class IntelligenceError(SkyVantaError):
    """Base exception for landing intelligence, safety supervision, and state machine decisions."""
    pass


class InvalidStateTransitionError(IntelligenceError):
    """Raised when a state transition violates state machine guards or topology rules."""
    pass


class StateTimeoutError(IntelligenceError):
    """Raised when a landing phase duration exceeds its configured maximum timeout."""
    pass


class SafetyInvariantViolationError(IntelligenceError):
    """Raised when an active safety supervisor invariant is breached."""
    pass


class FlightInterfaceError(SkyVantaError):
    """Base exception for flight interface, command validation, and autopilot operations."""
    pass


class CommandValidationError(FlightInterfaceError):
    """Raised when a flight command fails structural, temporal, or parameter validation."""
    pass


class CommandAuthorizationError(FlightInterfaceError):
    """Raised when a command fails safety supervisor authorization or violates flight mode rules."""
    pass


class AutopilotDisconnectedError(FlightInterfaceError):
    """Raised when an operation requires an active autopilot connection but the link is down."""
    pass


class CommandTimeoutError(FlightInterfaceError):
    """Raised when command acknowledgement or execution exceeds configured timeout thresholds."""
    pass


class RateLimitExceededError(FlightInterfaceError):
    """Raised when command transmission frequency exceeds allowable rate limits."""
    pass


class SimulationError(SkyVantaError):
    """Base exception for digital twin, scenario execution, and simulation engine errors."""
    pass


class ScenarioExecutionError(SimulationError):
    """Raised when scenario setup, execution, or validation invariants fail."""
    pass


class DigitalTwinDynamicsError(SimulationError):
    """Raised when physical integration, wind perturbation, or vehicle kinematics diverge."""
    pass






