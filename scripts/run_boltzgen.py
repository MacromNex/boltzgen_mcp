#!/usr/bin/env python
"""
Script to run BoltzGen with loguru logging.

Example usage:
    python scripts/run_boltzgen.py \
        --config example/vanilla_protein/1g13prot.yaml \
        --output workbench/test_run \
        --protocol protein-anything \
        --num_designs 10 \
        --budget 2
"""

import argparse
import subprocess
import sys
from pathlib import Path

from loguru import logger


def setup_logging(log_file: Path | None = None, verbose: bool = False) -> None:
    """Configure loguru logger."""
    logger.remove()  # Remove default handler

    # Console logging
    log_level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=log_level,
    )

    # File logging if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
            level="DEBUG",
            rotation="10 MB",
        )
        logger.info(f"Logging to file: {log_file}")


def run_boltzgen(
    config: str,
    output: str,
    protocol: str = "protein-anything",
    num_designs: int = 10,
    budget: int = 2,
    cuda_device: str | None = None,
    master_port: int = 29500,
) -> int:
    """
    Run BoltzGen with specified parameters.

    Args:
        config: Path to YAML configuration file
        output: Output directory path
        protocol: BoltzGen protocol to use
        num_designs: Number of designs to generate
        budget: Budget parameter
        cuda_device: CUDA device ID (e.g., "0" or "1")

    Returns:
        Exit code from the BoltzGen process
    """

    config_path = Path(config)

    # Validate config path early to avoid BoltzGen parsing directories
    if config_path.is_dir():
        logger.error(f"Config path is a directory, expected a YAML file: {config_path}")
        logger.error("Please pass a YAML design spec (e.g., example/nanobody/penguinpox.yaml)")
        return 1
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        return 1

    # Build command
    cmd = [
        "boltzgen",
        "run",
        str(config_path),
        "--output", output,
        "--protocol", protocol,
        "--num_designs", str(num_designs),
        "--budget", str(budget),
    ]

    # Set up environment (always copy so we can add transport fallbacks)
    import os

    env = os.environ.copy()

    if cuda_device is not None:
        env["CUDA_VISIBLE_DEVICES"] = cuda_device
        logger.info(f"Setting CUDA_VISIBLE_DEVICES={cuda_device}")

    # Force IPv4 loopback for torch.distributed to avoid AF errors and interface issues
    env["MASTER_ADDR"] = "127.0.0.1"
    env["MASTER_PORT"] = str(master_port)
    env["GLOO_SOCKET_IFNAME"] = "lo"
    env["NCCL_SOCKET_FAMILY"] = "AF_INET"
    env["NCCL_SOCKET_IFNAME"] = "lo"

    # Silence noisy warnings from dependencies
    # Blanket warning suppression; avoids CLI noise from torch/third-party libs
    env["PYTHONWARNINGS"] = "ignore"

    # Log command
    logger.info("Running BoltzGen with command:")
    logger.info(f"  {' '.join(cmd)}")
    logger.info(f"Config: {config}")
    logger.info(f"Output: {output}")
    logger.info(f"Protocol: {protocol}")
    logger.info(f"Num designs: {num_designs}")
    logger.info(f"Budget: {budget}")

    # Run process
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )

        # Stream output
        logger.info("BoltzGen started, streaming output:")
        logger.info("-" * 80)

        if process.stdout:
            for line in process.stdout:
                line = line.rstrip()
                if line:
                    logger.info(f"[BoltzGen] {line}")

        # Wait for completion
        return_code = process.wait()

        logger.info("-" * 80)
        if return_code == 0:
            logger.success(f"BoltzGen completed successfully!")
            logger.success(f"Results saved to: {output}")
        else:
            logger.error(f"BoltzGen failed with exit code: {return_code}")

        return return_code

    except FileNotFoundError:
        logger.error("BoltzGen command not found. Is it installed?")
        logger.error("Install with: pip install boltzgen")
        return 1
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        if process:
            process.terminate()
            process.wait()
        return 130
    except Exception as e:
        logger.exception(f"Error running BoltzGen: {e}")
        return 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run BoltzGen protein design with loguru logging",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to BoltzGen YAML configuration file",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output directory for results",
    )
    parser.add_argument(
        "--protocol",
        type=str,
        default="protein-anything",
        help="BoltzGen protocol to use",
    )
    parser.add_argument(
        "--num_designs",
        type=int,
        default=10,
        help="Number of designs to generate",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=2,
        help="Budget parameter for BoltzGen",
    )
    parser.add_argument(
        "--cuda_device",
        type=str,
        default=None,
        help="CUDA device to use (e.g., '0' or '1')",
    )
    parser.add_argument(
        "--master_port",
        type=int,
        default=29500,
        help="Port for torch.distributed master (set a free port if needed)",
    )
    parser.add_argument(
        "--log_file",
        type=str,
        default=None,
        help="Optional log file path",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )

    args = parser.parse_args()

    # Setup logging
    log_file = Path(args.log_file) if args.log_file else None
    setup_logging(log_file=log_file, verbose=args.verbose)

    logger.info("=" * 80)
    logger.info("BoltzGen Runner")
    logger.info("=" * 80)

    # Run BoltzGen
    exit_code = run_boltzgen(
        config=args.config,
        output=args.output,
        protocol=args.protocol,
        num_designs=args.num_designs,
        budget=args.budget,
        cuda_device=args.cuda_device,
        master_port=args.master_port,
    )

    logger.info("=" * 80)
    logger.info("Done")
    logger.info("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
