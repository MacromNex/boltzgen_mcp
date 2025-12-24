#!/usr/bin/env python3
"""
Script: protein_binder_design.py
Description: Design protein binders using BoltzGen with protein-anything protocol

Original Use Case: examples/use_case_1_protein_binder_design.py
Dependencies Removed: scripts.run_boltzgen (inlined), loguru (simplified)

Usage:
    python scripts/protein_binder_design.py --input <config_file> --output <output_dir>

Example:
    python scripts/protein_binder_design.py --input examples/data/1g13prot.yaml --output results/protein_design
"""

# ==============================================================================
# Minimal Imports (only essential packages)
# ==============================================================================
import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Union, Optional, Dict, Any
import json

# ==============================================================================
# Configuration (extracted from use case)
# ==============================================================================
DEFAULT_CONFIG = {
    "protocol": "protein-anything",
    "num_designs": 10,
    "budget": 2,
    "master_port": 29500,
    "verbose": True
}

# ==============================================================================
# Inlined Utility Functions (simplified from repo)
# ==============================================================================
def setup_simple_logging(verbose: bool = False) -> None:
    """Simple logging setup without loguru dependency."""
    import logging
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        level=level
    )

def log_info(message: str) -> None:
    """Simple info logging."""
    print(f"INFO: {message}")

def log_success(message: str) -> None:
    """Simple success logging."""
    print(f"SUCCESS: {message}")

def log_error(message: str) -> None:
    """Simple error logging."""
    print(f"ERROR: {message}")

def validate_config_file(config_path: Path) -> bool:
    """Validate config file exists and is valid."""
    if config_path.is_dir():
        log_error(f"Config path is a directory, expected a YAML file: {config_path}")
        return False
    if not config_path.exists():
        log_error(f"Configuration file not found: {config_path}")
        return False
    return True

# ==============================================================================
# Core Function (main logic extracted from use case)
# ==============================================================================
def run_protein_binder_design(
    input_file: Union[str, Path],
    output_file: Optional[Union[str, Path]] = None,
    config: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Main function for protein binder design using BoltzGen.

    Args:
        input_file: Path to YAML configuration file
        output_file: Path to save output directory (optional)
        config: Configuration dict (uses DEFAULT_CONFIG if not provided)
        **kwargs: Override specific config parameters

    Returns:
        Dict containing:
            - result: Main computation result (exit code)
            - output_file: Path to output directory
            - metadata: Execution metadata

    Example:
        >>> result = run_protein_binder_design("examples/data/1g13prot.yaml", "results/protein_design")
        >>> print(result['output_file'])
    """
    # Setup
    input_file = Path(input_file)
    config_merged = {**DEFAULT_CONFIG, **(config or {}), **kwargs}

    # Validate input
    if not validate_config_file(input_file):
        return {
            "result": 1,
            "output_file": None,
            "metadata": {"error": "Invalid config file", "input_file": str(input_file)}
        }

    # Determine output directory
    if output_file is None:
        output_file = f"results/protein_binder_{input_file.stem}"
    output_path = Path(output_file)

    log_info("=" * 80)
    log_info("BoltzGen Protein Binder Design")
    log_info("=" * 80)
    log_info(f"Protocol: {config_merged['protocol']}")
    log_info(f"Config file: {input_file}")
    log_info(f"Output directory: {output_path}")
    log_info(f"Number of designs: {config_merged['num_designs']}")
    log_info(f"Budget: {config_merged['budget']}")

    # Build BoltzGen command
    cmd = [
        "boltzgen",
        "run",
        str(input_file),
        "--output", str(output_path),
        "--protocol", config_merged["protocol"],
        "--num_designs", str(config_merged["num_designs"]),
        "--budget", str(config_merged["budget"]),
    ]

    # Set up environment
    env = os.environ.copy()

    # CUDA device handling
    if config_merged.get("cuda_device") is not None:
        env["CUDA_VISIBLE_DEVICES"] = str(config_merged["cuda_device"])
        log_info(f"Setting CUDA_VISIBLE_DEVICES={config_merged['cuda_device']}")

    # Network settings for torch.distributed
    env["MASTER_ADDR"] = "127.0.0.1"
    env["MASTER_PORT"] = str(config_merged["master_port"])
    env["GLOO_SOCKET_IFNAME"] = "lo"
    env["NCCL_SOCKET_FAMILY"] = "AF_INET"
    env["NCCL_SOCKET_IFNAME"] = "lo"
    env["PYTHONWARNINGS"] = "ignore"

    # Log command
    log_info("Running BoltzGen with command:")
    log_info(f"  {' '.join(cmd)}")

    # Execute BoltzGen
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )

        log_info("BoltzGen started, streaming output:")
        log_info("-" * 80)

        if process.stdout:
            for line in process.stdout:
                line = line.rstrip()
                if line:
                    if config_merged.get("verbose", False):
                        print(f"[BoltzGen] {line}")

        # Wait for completion
        return_code = process.wait()

        log_info("-" * 80)
        if return_code == 0:
            log_success("Protein binder design completed successfully!")
            log_info(f"Results saved to: {output_path}")

            # Count generated files
            if output_path.exists():
                cif_files = list(output_path.glob("*.cif"))
                pdb_files = list(output_path.glob("*.pdb"))
                structure_files = cif_files + pdb_files
                log_info(f"Generated {len(structure_files)} structure files ({len(cif_files)} CIF, {len(pdb_files)} PDB)")
        else:
            log_error(f"BoltzGen failed with exit code: {return_code}")

        return {
            "result": return_code,
            "output_file": str(output_path) if return_code == 0 else None,
            "metadata": {
                "input_file": str(input_file),
                "config": config_merged,
                "exit_code": return_code
            }
        }

    except FileNotFoundError:
        log_error("BoltzGen command not found. Is it installed?")
        return {
            "result": 1,
            "output_file": None,
            "metadata": {"error": "BoltzGen not found", "input_file": str(input_file)}
        }
    except KeyboardInterrupt:
        log_error("Process interrupted by user")
        if process:
            process.terminate()
            process.wait()
        return {
            "result": 130,
            "output_file": None,
            "metadata": {"error": "Interrupted", "input_file": str(input_file)}
        }
    except Exception as e:
        log_error(f"Error running BoltzGen: {e}")
        return {
            "result": 1,
            "output_file": None,
            "metadata": {"error": str(e), "input_file": str(input_file)}
        }

# ==============================================================================
# CLI Interface
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--input', '-i', required=True, help='Input YAML config file path')
    parser.add_argument('--output', '-o', help='Output directory path')
    parser.add_argument('--config', '-c', help='Config file (JSON)')

    # BoltzGen specific arguments
    parser.add_argument('--num_designs', type=int, help='Number of designs to generate')
    parser.add_argument('--budget', type=int, help='Number of final diverse designs')
    parser.add_argument('--cuda_device', help='CUDA device ID (e.g., "0")')
    parser.add_argument('--master_port', type=int, help='Distributed master port')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')

    args = parser.parse_args()

    # Setup logging
    setup_simple_logging(verbose=args.verbose)

    # Load config if provided
    config = None
    if args.config:
        with open(args.config) as f:
            config = json.load(f)

    # Override config with CLI args
    cli_overrides = {}
    if args.num_designs is not None:
        cli_overrides['num_designs'] = args.num_designs
    if args.budget is not None:
        cli_overrides['budget'] = args.budget
    if args.cuda_device is not None:
        cli_overrides['cuda_device'] = args.cuda_device
    if args.master_port is not None:
        cli_overrides['master_port'] = args.master_port
    if args.verbose:
        cli_overrides['verbose'] = args.verbose

    # Run
    result = run_protein_binder_design(
        input_file=args.input,
        output_file=args.output,
        config=config,
        **cli_overrides
    )

    if result['result'] == 0:
        print(f"✅ Success: {result.get('output_file', 'Completed')}")
    else:
        print(f"❌ Failed with exit code: {result['result']}")

    return result['result']

if __name__ == '__main__':
    sys.exit(main())