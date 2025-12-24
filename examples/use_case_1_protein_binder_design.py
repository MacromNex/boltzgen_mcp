#!/usr/bin/env python
"""
Use Case 1: Protein Binder Design using BoltzGen

This script demonstrates the most common use case of BoltzGen - designing protein
binders against protein targets using the 'protein-anything' protocol.

Example Usage:
    python examples/use_case_1_protein_binder_design.py \
        --config examples/data/1g13prot.yaml \
        --output examples/results/protein_binder_1g13 \
        --num_designs 10 \
        --budget 2

    # With custom parameters:
    python examples/use_case_1_protein_binder_design.py \
        --config examples/data/1g13prot.yaml \
        --output examples/results/protein_binder_1g13_custom \
        --num_designs 50 \
        --budget 5 \
        --cuda_device 0
"""

import argparse
import os
import sys
from pathlib import Path

# Add the scripts directory to path for importing run_boltzgen
sys.path.append(str(Path(__file__).parent.parent / "scripts"))
from run_boltzgen import run_boltzgen, setup_logging

from loguru import logger


def main():
    parser = argparse.ArgumentParser(
        description="Use Case 1: Protein Binder Design with BoltzGen",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--config",
        type=str,
        default="examples/data/1g13prot.yaml",
        help="Path to BoltzGen YAML configuration file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="examples/results/protein_binder_1g13",
        help="Output directory for results"
    )
    parser.add_argument(
        "--num_designs",
        type=int,
        default=10,
        help="Number of designs to generate (10-60000 for production)"
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
    logger.info("BoltzGen Use Case 1: Protein Binder Design")
    logger.info("=" * 80)

    logger.info(f"Protocol: protein-anything (default for protein binder design)")
    logger.info(f"Use Case: Design proteins that bind to protein targets")
    logger.info(f"Config file: {args.config}")
    logger.info(f"Output directory: {args.output}")
    logger.info(f"Number of designs: {args.num_designs}")
    logger.info(f"Budget (final diverse designs): {args.budget}")

    # Validate config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        logger.error("Please ensure the config file exists or use the default:")
        logger.error("  examples/data/1g13prot.yaml")
        return 1

    # Run BoltzGen with protein-anything protocol
    exit_code = run_boltzgen(
        config=args.config,
        output=args.output,
        protocol="protein-anything",  # Default protocol for protein binder design
        num_designs=args.num_designs,
        budget=args.budget,
        cuda_device=args.cuda_device,
    )

    logger.info("=" * 80)
    if exit_code == 0:
        logger.success("Protein binder design completed successfully!")
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
    else:
        logger.error(f"Design failed with exit code: {exit_code}")

    logger.info("=" * 80)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())