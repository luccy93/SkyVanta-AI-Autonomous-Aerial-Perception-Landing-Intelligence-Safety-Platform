"""Command-line interface for SkyVanta AI."""

import argparse
import sys
from skyvanta.core.config import SkyVantaConfig
from skyvanta.core.logging import get_logger
from skyvanta.pipeline.runner import PipelineRunner
from skyvanta.simulation.benchmark import SimulationBenchmark
from skyvanta.simulation.monte_carlo import MonteCarloRunner
from skyvanta.simulation.registry import ScenarioRegistry
from skyvanta.simulation.reports import ScenarioReportGenerator
from skyvanta.simulation.runner import DigitalTwinRunner

logger = get_logger("skyvanta.cli")


def build_parser() -> argparse.ArgumentParser:
    """Builds command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="skyvanta",
        description="SkyVanta AI — Autonomous Aerial Perception, Landing Intelligence & Digital Twin Validation",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default=None,
        help="Optional positional command (e.g. 'demo')",
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
        help="Path to output rendered video file or experiment result JSON",
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
    # Volume 9 Digital Twin & Scenario Options
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Execute a specific named Digital Twin scenario (e.g. 'nominal_landing', 'target_loss')",
    )
    parser.add_argument(
        "--monte-carlo",
        type=str,
        default=None,
        help="Execute a Monte Carlo simulation batch for a named scenario",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=20,
        help="Number of iterations for Monte Carlo simulation batch (default 20)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Deterministic random seed override",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List all registered benchmark scenarios",
    )
    parser.add_argument(
        "--benchmark-simulation",
        action="store_true",
        help="Run performance benchmark on simulation throughput",
    )
    # Volume D9 Release Engineering & Verification
    parser.add_argument(
        "--release",
        action="store_true",
        help="Run pre-flight release verification and print readiness report",
    )
    return parser


def run_release_verification() -> int:
    """Executes pre-flight release verification and formats summary report."""
    import os
    from skyvanta.deployment.config import DeploymentConfig
    from skyvanta.deployment.release import ReleaseManifest, ReleaseVerifier

    dep_cfg = DeploymentConfig.from_env()
    manifest = ReleaseManifest.generate(
        environment=dep_cfg.environment.value,
        test_count=399,
        base_dir=os.getcwd(),
    )
    if dep_cfg.git_commit:
        manifest.git_commit = dep_cfg.git_commit

    verifier = ReleaseVerifier()
    result = verifier.verify(deployment_config=dep_cfg, manifest=manifest)

    hw_str = "DISABLED" if not manifest.hardware_access else "ENABLED"
    ext_str = "DISABLED" if not dep_cfg.allow_external else "ENABLED"
    mod_str = "DISABLED" if not manifest.network_model_download else "ENABLED"

    health_status = "PASS" if result.checks.get("health_service_operational", False) else "FAIL"
    config_status = "PASS" if result.checks.get("hardware_isolation", False) and result.checks.get("version_valid", False) else "FAIL"
    security_status = "PASS" if result.checks.get("secret_isolation", False) else "FAIL"
    release_status = "PASS" if result.passed else "FAIL"
    status_label = "READY" if result.passed else "FAILED"

    print("SkyVanta AI Release Verification")
    print("---------------------------------")
    print(f"Version:              {manifest.version}")
    print(f"Git Commit:           {manifest.git_commit}")
    print(f"Environment:          {manifest.deployment_environment}")
    print(f"Core Architecture:    {manifest.core_architecture_version}")
    print("")
    print(f"Hardware Access:      {hw_str}")
    print(f"External Access:      {ext_str}")
    print(f"Model Downloads:      {mod_str}")
    print("")
    print(f"Health:               {health_status}")
    print(f"Configuration:        {config_status}")
    print(f"Security:             {security_status}")
    print(f"Release Verification: {release_status}")
    print("")
    print(f"RELEASE STATUS:       {status_label}")

    if not result.passed:
        if result.failures:
            print("\nFailures:")
            for f in result.failures:
                print(f"  - {f}")
        return 1
    return 0


def main() -> None:
    """CLI execution entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    # 0. Check Release Subcommand / Option
    if args.command == "release" or args.release:
        sys.exit(run_release_verification())

    # 1. Check List Scenarios
    if args.list_scenarios:
        print("Available SkyVanta AI Standard Benchmark Scenarios:")
        for name in ScenarioRegistry.list_all():
            scen = ScenarioRegistry.get(name)
            desc = scen.description if scen else ""
            print(f"  - {name:<24}: {desc}")
        return

    # 2. Check Single Scenario Execution
    if args.scenario:
        runner = DigitalTwinRunner()
        try:
            result, traj = runner.run_named_scenario(args.scenario, seed=args.seed)
            md_report = ScenarioReportGenerator.generate_single_run_markdown(result)
            print(md_report)

            if args.output:
                ScenarioReportGenerator.export_json(result, args.output)
                print(f"Experiment result exported to: {args.output}")

            if not result.metrics.success:
                sys.exit(1)
            return
        except Exception as e:
            logger.error("Scenario execution failed: %s", e)
            sys.exit(1)

    # 3. Check Monte Carlo Execution
    if args.monte_carlo:
        scen = ScenarioRegistry.get(args.monte_carlo)
        if scen is None:
            logger.error("Unknown scenario for Monte Carlo: '%s'", args.monte_carlo)
            sys.exit(1)

        base_seed = args.seed if args.seed is not None else scen.seed
        mc_runner = MonteCarloRunner()
        try:
            stats, results = mc_runner.run_batch(scen, number_of_runs=args.runs, base_seed=base_seed)
            md_report = ScenarioReportGenerator.generate_monte_carlo_markdown(stats, scen.name)
            print(md_report)
            return
        except Exception as e:
            logger.error("Monte Carlo batch failed: %s", e)
            sys.exit(1)

    # 4. Check Benchmark Simulation
    if args.benchmark_simulation:
        scen = ScenarioRegistry.get("nominal_landing") or ScenarioRegistry.get_all_scenarios()[0]
        bench = SimulationBenchmark()
        stats = bench.benchmark_scenario(scen, iterations=5)
        print("Simulation Performance Benchmark Results:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        return

    # 5. Core Video / Demo Pipeline
    config = SkyVantaConfig.from_yaml(args.config) if args.config else SkyVantaConfig()

    if args.no_yolo:
        config.perception.detector.use_yolo = False
    elif args.yolo:
        config.perception.detector.use_yolo = True

    runner = PipelineRunner(config)

    try:
        if args.input:
            runner.process_video(args.input, output_path=args.output)
        elif args.demo or args.command == "demo" or len(sys.argv) == 1:
            runner.run_demo(output_path=args.output)
        else:
            parser.print_help()

    except Exception as e:
        logger.error("Execution failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
