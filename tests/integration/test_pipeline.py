"""Integration tests for end-to-end SkyVanta pipeline execution."""

import os
import tempfile
import pytest
from skyvanta.core.config import SkyVantaConfig
from skyvanta.pipeline.runner import PipelineRunner


def test_pipeline_demo_short_run():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = os.path.join(tmpdir, "test_demo.mp4")
        config = SkyVantaConfig()
        config.pipeline.demo_duration_sec = 0.5  # 15 frames for quick test
        config.pipeline.output_dir = tmpdir
        config.detector.use_yolo = False

        runner = PipelineRunner(config)
        result_path = runner.run_demo(output_path=out_file)

        assert os.path.exists(result_path)
        assert os.path.getsize(result_path) > 1000  # Non-empty video file
