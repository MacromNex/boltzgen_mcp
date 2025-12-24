#!/usr/bin/env python
"""
Use Case 5: Antibody CDR Design using BoltzGen

This script demonstrates antibody CDR (Complementarity Determining Region) design
using the 'antibody-anything' protocol. This protocol filters cysteines and is
optimized for full antibody (Fab) structure design.

Example Usage:
    python examples/use_case_5_antibody_design.py \
        --config examples/data/pdl1.yaml \
        --output examples/results/antibody_design_pdl1 \
        --num_designs 10 \
        --budget 2

    # With custom parameters:
    python examples/use_case_5_antibody_design.py \
        --config examples/data/pdl1.yaml \
        --output examples/results/antibody_custom \
        --num_designs 50 \
        --budget 5 \
        --cuda_device 0
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Add the scripts directory to path for importing run_boltzgen
sys.path.append(str(Path(__file__).parent.parent / "scripts"))
from run_boltzgen import setup_logging

from loguru import logger


def run_antibody_boltzgen(
    config: str,
    output: str,
    num_designs: int = 10,
    budget: int = 2,
    cuda_device: str = None,
) -> int:
    """
    Run BoltzGen with antibody-anything protocol.

    Args:
        config: Path to YAML configuration file
        output: Output directory path
        num_designs: Number of designs to generate
        budget: Budget parameter
        cuda_device: CUDA device ID (e.g., "0" or "1")

    Returns:
        Exit code from the BoltzGen process
    """

    # Build command
    cmd = [
        "boltzgen",
        "run",
        config,
        "--output", output,
        "--protocol", "antibody-anything",  # Specialized for antibody CDR design
        "--num_designs", str(num_designs),
        "--budget", str(budget),
    ]

    # Set up environment
    env = os.environ.copy()
    if cuda_device is not None:
        env["CUDA_VISIBLE_DEVICES"] = cuda_device
        logger.info(f"Setting CUDA_VISIBLE_DEVICES={cuda_device}")

    # Network settings for torch.distributed
    env["MASTER_ADDR"] = "127.0.0.1"
    env["MASTER_PORT"] = "29500"
    env["GLOO_SOCKET_IFNAME"] = "lo"
    env["NCCL_SOCKET_FAMILY"] = "AF_INET"
    env["NCCL_SOCKET_IFNAME"] = "lo"
    env["PYTHONWARNINGS"] = "ignore"

    # Log command
    logger.info("Running BoltzGen with antibody-anything protocol:")
    logger.info(f"  {' '.join(cmd)}")

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
            logger.success("Antibody design completed successfully!")
        else:
            logger.error(f"Antibody design failed with exit code: {return_code}")

        return return_code

    except FileNotFoundError:
        logger.error("BoltzGen command not found. Is it installed?")
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


def main():
    parser = argparse.ArgumentParser(
        description="Use Case 5: Antibody CDR Design with BoltzGen",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--config",
        type=str,
        default="examples/data/pdl1_simplified.yaml",
        help="Path to BoltzGen YAML configuration file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="examples/results/antibody_design_pdl1",
        help="Output directory for results"
    )
    parser.add_argument(
        "--num_designs",
        type=int,
        default=10,
        help="Number of designs to generate"
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=2,
        help="Number of final diverse designs after filtering"
    )
    parser.add_argument(
        "--cuda_device",
        type=str,
        default=None,
        help="CUDA device to use (e.g., '0' or '1')"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose)

    logger.info("=" * 80)
    logger.info("BoltzGen Use Case 5: Antibody CDR Design")
    logger.info("=" * 80)

    logger.info(f"Protocol: antibody-anything")
    logger.info(f"Use Case: Design antibody CDRs (Complementarity Determining Regions)")
    logger.info(f"Features: Filters cysteines, optimized for full antibody (Fab) design")
    logger.info(f"Config file: {args.config}")
    logger.info(f"Output directory: {args.output}")
    logger.info(f"Number of designs: {args.num_designs}")
    logger.info(f"Budget: {args.budget}")

    # Validate config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        logger.error("Please ensure the config file exists or use the default:")
        logger.error("  examples/data/pdl1_simplified.yaml")
        return 1

    # Run BoltzGen with antibody-anything protocol
    exit_code = run_antibody_boltzgen(
        config=args.config,
        output=args.output,
        num_designs=args.num_designs,
        budget=args.budget,
        cuda_device=args.cuda_device,
    )

    logger.info("=" * 80)
    if exit_code == 0:
        logger.success("Antibody CDR design completed successfully!")
        logger.info(f"Results available in: {args.output}")
        logger.info("Generated files:")

        output_path = Path(args.output)
        if output_path.exists():
            pdb_files = list(output_path.glob("*.pdb"))
            logger.info(f"  - {len(pdb_files)} PDB structure files")

            # List first few PDB files as examples
            for i, pdb_file in enumerate(pdb_files[:3]):
                logger.info(f"    {pdb_file.name}")
            if len(pdb_files) > 3:
                logger.info(f"    ... and {len(pdb_files) - 3} more")

        logger.info("\nAntibody protocol features:")
        logger.info("  - Cysteine filtering enabled")
        logger.info("  - Optimized for full antibody (Fab) design")
        logger.info("  - Specialized for heavy and light chain CDR design")
        logger.info("  - Compatible with multiple antibody scaffolds")
    else:
        logger.error(f"Design failed with exit code: {exit_code}")

    logger.info("=" * 80)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())