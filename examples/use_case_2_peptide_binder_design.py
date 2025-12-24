#!/usr/bin/env python
"""
Use Case 2: Peptide Binder Design using BoltzGen

This script demonstrates peptide binder design against protein targets using
the 'peptide-anything' protocol. This protocol filters cysteines and uses
lower diversity parameters optimized for peptide design.

Example Usage:
    python examples/use_case_2_peptide_binder_design.py \
        --config examples/data/beetletert.yaml \
        --output examples/results/peptide_binder_beetletert \
        --num_designs 10 \
        --budget 2

    # With alpha parameter for diversity control:
    python examples/use_case_2_peptide_binder_design.py \
        --config examples/data/beetletert.yaml \
        --output examples/results/peptide_binder_custom \
        --num_designs 50 \
        --budget 5 \
        --alpha 0.01 \
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


def run_peptide_boltzgen(
    config: str,
    output: str,
    num_designs: int = 10,
    budget: int = 2,
    alpha: float = None,
    cuda_device: str = None,
) -> int:
    """
    Run BoltzGen with peptide-anything protocol.

    Args:
        config: Path to YAML configuration file
        output: Output directory path
        num_designs: Number of designs to generate
        budget: Budget parameter
        alpha: Diversity vs quality tradeoff (0.0=quality only, 1.0=diversity only)
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
        "--protocol", "peptide-anything",  # Specialized protocol for peptides
        "--num_designs", str(num_designs),
        "--budget", str(budget),
    ]

    # Add alpha parameter if specified
    if alpha is not None:
        cmd.extend(["--alpha", str(alpha)])

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
    logger.info("Running BoltzGen with peptide-anything protocol:")
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
            logger.success("Peptide design completed successfully!")
        else:
            logger.error(f"Peptide design failed with exit code: {return_code}")

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
        description="Use Case 2: Peptide Binder Design with BoltzGen",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--config",
        type=str,
        default="examples/data/beetletert.yaml",
        help="Path to BoltzGen YAML configuration file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="examples/results/peptide_binder_beetletert",
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
        "--alpha",
        type=float,
        default=None,
        help="Diversity vs quality tradeoff (0.0=quality only, 1.0=diversity only)"
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
    logger.info("BoltzGen Use Case 2: Peptide Binder Design")
    logger.info("=" * 80)

    logger.info(f"Protocol: peptide-anything (specialized for peptides)")
    logger.info(f"Use Case: Design peptides (including cyclic) that bind to protein targets")
    logger.info(f"Features: Filters cysteines by default, optimized diversity parameters")
    logger.info(f"Config file: {args.config}")
    logger.info(f"Output directory: {args.output}")
    logger.info(f"Number of designs: {args.num_designs}")
    logger.info(f"Budget: {args.budget}")
    if args.alpha is not None:
        logger.info(f"Alpha (diversity): {args.alpha}")

    # Validate config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        logger.error("Please ensure the config file exists or use the default:")
        logger.error("  examples/data/beetletert.yaml")
        return 1

    # Run BoltzGen with peptide-anything protocol
    exit_code = run_peptide_boltzgen(
        config=args.config,
        output=args.output,
        num_designs=args.num_designs,
        budget=args.budget,
        alpha=args.alpha,
        cuda_device=args.cuda_device,
    )

    logger.info("=" * 80)
    if exit_code == 0:
        logger.success("Peptide binder design completed successfully!")
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

        logger.info("\nNote: Peptide protocol features:")
        logger.info("  - Cysteine filtering enabled by default")
        logger.info("  - Lower diversity parameters for peptide optimization")
        logger.info("  - Suitable for linear and cyclic peptides")
    else:
        logger.error(f"Design failed with exit code: {exit_code}")

    logger.info("=" * 80)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())