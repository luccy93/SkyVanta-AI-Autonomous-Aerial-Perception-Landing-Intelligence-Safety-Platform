"""SkyVanta AI — Autonomous Aerial Perception, Landing Intelligence & Safety Platform.

Volume 1: Architecture Foundation & Modular Pipeline.
"""

__version__ = "0.1.0"
__author__ = "SkyVanta-AI / Devendraprasad"

from skyvanta.core.config import SkyVantaConfig
from skyvanta.pipeline.runner import PipelineRunner

__all__ = ["SkyVantaConfig", "PipelineRunner", "__version__"]
