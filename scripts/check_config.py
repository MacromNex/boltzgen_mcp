#!/usr/bin/env python
"""
Script to validate BoltzGen configuration files with loguru logging.

Example usage:
    # Check a single config file
    python scripts/check_config.py --config example/vanilla_protein/1g13prot.yaml

    # Check multiple config files
    python scripts/check_config.py --config config1.yaml config2.yaml config3.yaml

    # Check all configs in a directory
    python scripts/check_config.py --config-dir examples/
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List

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


def check_config(config_path: str) -> bool:
    """
    Check a single BoltzGen configuration file.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        True if valid, False if invalid
    """
    config_path_obj = Path(config_path)

    if not config_path_obj.exists():
        logger.error(f"Config file not found: {config_path}")
        return False

    logger.info(f"Checking config: {config_path}")

    # Build command
    cmd = ["boltzgen", "check", config_path]

    try:
        # Run the check command
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )

        # Log output
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    logger.debug(f"  [boltzgen check] {line}")

        # Check result
        if result.returncode == 0:
            logger.success(f"✓ Config is valid: {config_path}")
            return True
        else:
            logger.error(f"✗ Config is invalid: {config_path}")
            if result.stdout:
                logger.error("Error details:")
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        logger.error(f"  {line}")
            return False

    except FileNotFoundError:
        logger.error("BoltzGen command not found. Is it installed?")
        logger.error("Install with: pip install boltzgen")
        return False
    except Exception as e:
        logger.exception(f"Error checking config {config_path}: {e}")
        return False


def find_yaml_files(directory: Path) -> List[Path]:
    """
    Find all YAML files in a directory recursively.

    Args:
        directory: Directory to search

    Returns:
        List of YAML file paths
    """
    yaml_files = []
    for pattern in ["**/*.yaml", "**/*.yml"]:
        yaml_files.extend(directory.glob(pattern))
    return sorted(yaml_files)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate BoltzGen configuration files with loguru logging",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--config",
        type=str,
        nargs="+",
        help="Path(s) to BoltzGen YAML configuration file(s)",
    )
    parser.add_argument(
        "--config-dir",
        type=str,
        help="Directory containing config files (will check all .yaml files recursively)",
    )
    parser.add_argument(
        "--log-file",
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

    # Validate arguments
    if not args.config and not args.config_dir:
        parser.error("Either --config or --config-dir must be specified")

    # Setup logging
    log_file = Path(args.log_file) if args.log_file else None
    setup_logging(log_file=log_file, verbose=args.verbose)

    logger.info("=" * 80)
    logger.info("BoltzGen Config Validator")
    logger.info("=" * 80)

    # Collect config files to check
    config_files = []

    if args.config:
        config_files.extend(args.config)

    if args.config_dir:
        config_dir = Path(args.config_dir)
        if not config_dir.exists():
            logger.error(f"Config directory not found: {args.config_dir}")
            return 1
        if not config_dir.is_dir():
            logger.error(f"Not a directory: {args.config_dir}")
            return 1

        found_files = find_yaml_files(config_dir)
        logger.info(f"Found {len(found_files)} YAML file(s) in {args.config_dir}")
        config_files.extend([str(f) for f in found_files])

    if not config_files:
        logger.warning("No config files to check")
        return 0

    logger.info(f"Checking {len(config_files)} config file(s)...")
    logger.info("-" * 80)

    # Check all configs
    results = {}
    for config_path in config_files:
        is_valid = check_config(config_path)
        results[config_path] = is_valid
        logger.info("-" * 80)

    # Summary
    logger.info("=" * 80)
    logger.info("Summary")
    logger.info("=" * 80)

    valid_count = sum(1 for v in results.values() if v)
    invalid_count = sum(1 for v in results.values() if not v)

    logger.info(f"Total configs checked: {len(results)}")
    logger.info(f"Valid configs: {valid_count}")
    logger.info(f"Invalid configs: {invalid_count}")

    if invalid_count > 0:
        logger.info("")
        logger.error("Invalid config files:")
        for config_path, is_valid in results.items():
            if not is_valid:
                logger.error(f"  ✗ {config_path}")

    if valid_count > 0:
        logger.info("")
        logger.success("Valid config files:")
        for config_path, is_valid in results.items():
            if is_valid:
                logger.success(f"  ✓ {config_path}")

    logger.info("=" * 80)
    logger.info("Done")
    logger.info("=" * 80)

    # Return non-zero exit code if any configs are invalid
    return 1 if invalid_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
