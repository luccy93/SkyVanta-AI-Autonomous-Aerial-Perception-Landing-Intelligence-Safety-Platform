"""Command-line interface for SkyVanta AI."""

import argparse
import sys
from skyvanta.core.config import SkyVantaConfig
from skyvanta.core.logging import get_logger
from skyvanta.pipeline.runner import PipelineRunner

logger = get_logger("skyvanta.cli")


def build_parser() -> argparse.ArgumentParser:
    """Builds command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="skyvanta",
        description="SkyVanta AI — Autonomous Aerial Perception & Landing Intelligence Platform",
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        default=None,
        help="Path to input video file (e.g. video.mp4)",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Path to output rendered video file",
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        help="Path to custom YAML configuration file",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run procedural synthetic aerial demonstration",
    )
    parser.add_argument(
        "--yolo",
        action="store_true",
        default=None,
        help="Force enable YOLO object detection",
    )
    parser.add_argument(
        "--no-yolo",
        action="store_true",
        help="Disable YOLO object detection (use motion contrast only)",
    )
    return parser


def main() -> None:
    """CLI execution entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    config = SkyVantaConfig.from_yaml(args.config) if args.config else SkyVantaConfig()

    if args.no_yolo:
        config.detector.use_yolo = False
    elif args.yolo:
        config.detector.use_yolo = True

    runner = PipelineRunner(config)

    try:
        if args.input:
            runner.process_video(args.input, output_path=args.output)
        elif args.demo or len(sys.argv) == 1:
            runner.run_demo(output_path=args.output)
        else:
            parser.print_help()
    except Exception as e:
        logger.error("Execution failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
