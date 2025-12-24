"""
BoltzGen execution utilities for MCP scripts.

This module contains common BoltzGen execution logic extracted from use cases.
"""

import os
import subprocess
from pathlib import Path
from typing import Union, Dict, Any, Optional

from .utils import log_info, log_success, log_error
from .io import validate_config_file, count_structure_files


def setup_boltzgen_environment(
    cuda_device: Optional[str] = None,
    master_port: int = 29500
) -> Dict[str, str]:
    """Set up environment for BoltzGen execution."""
    env = os.environ.copy()

    # CUDA device handling
    if cuda_device is not None:
        env["CUDA_VISIBLE_DEVICES"] = str(cuda_device)
        log_info(f"Setting CUDA_VISIBLE_DEVICES={cuda_device}")

    # Network settings for torch.distributed
    env["MASTER_ADDR"] = "127.0.0.1"
    env["MASTER_PORT"] = str(master_port)
    env["GLOO_SOCKET_IFNAME"] = "lo"
    env["NCCL_SOCKET_FAMILY"] = "AF_INET"
    env["NCCL_SOCKET_IFNAME"] = "lo"
    env["PYTHONWARNINGS"] = "ignore"

    return env


def build_boltzgen_command(
    config_file: Union[str, Path],
    output_dir: Union[str, Path],
    protocol: str,
    num_designs: int,
    budget: int,
    alpha: Optional[float] = None,
    **kwargs
) -> list:
    """Build BoltzGen command line."""
    cmd = [
        "boltzgen",
        "run",
        str(config_file),
        "--output", str(output_dir),
        "--protocol", protocol,
        "--num_designs", str(num_designs),
        "--budget", str(budget),
    ]

    # Add alpha parameter if specified (peptide-specific)
    if alpha is not None:
        cmd.extend(["--alpha", str(alpha)])

    # Add any additional arguments
    for key, value in kwargs.items():
        if value is not None:
            cmd.extend([f"--{key}", str(value)])

    return cmd


def execute_boltzgen(
    config_file: Union[str, Path],
    output_dir: Union[str, Path],
    protocol: str,
    num_designs: int = 10,
    budget: int = 2,
    alpha: Optional[float] = None,
    cuda_device: Optional[str] = None,
    master_port: int = 29500,
    verbose: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Execute BoltzGen with given parameters.

    Returns:
        Dict containing:
            - result: Exit code
            - output_file: Path to output directory (if successful)
            - metadata: Execution metadata
    """
    config_path = Path(config_file)
    output_path = Path(output_dir)

    # Validate config file
    if not validate_config_file(config_path):
        return {
            "result": 1,
            "output_file": None,
            "metadata": {"error": "Invalid config file", "input_file": str(config_path)}
        }

    # Build command
    cmd = build_boltzgen_command(
        config_file=config_path,
        output_dir=output_path,
        protocol=protocol,
        num_designs=num_designs,
        budget=budget,
        alpha=alpha,
        **kwargs
    )

    # Set up environment
    env = setup_boltzgen_environment(cuda_device=cuda_device, master_port=master_port)

    # Log command
    log_info("Running BoltzGen with command:")
    log_info(f"  {' '.join(cmd)}")

    # Execute
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
                if line and verbose:
                    print(f"[BoltzGen] {line}")

        # Wait for completion
        return_code = process.wait()

        log_info("-" * 80)
        if return_code == 0:
            log_success(f"BoltzGen completed successfully!")
            log_info(f"Results saved to: {output_path}")

            # Count generated files
            file_counts = count_structure_files(output_path)
            log_info(f"Generated {file_counts['total']} structure files ({file_counts['cif']} CIF, {file_counts['pdb']} PDB)")
        else:
            log_error(f"BoltzGen failed with exit code: {return_code}")

        return {
            "result": return_code,
            "output_file": str(output_path) if return_code == 0 else None,
            "metadata": {
                "input_file": str(config_path),
                "protocol": protocol,
                "num_designs": num_designs,
                "budget": budget,
                "exit_code": return_code,
                "file_counts": file_counts if return_code == 0 else None
            }
        }

    except FileNotFoundError:
        log_error("BoltzGen command not found. Is it installed?")
        return {
            "result": 1,
            "output_file": None,
            "metadata": {"error": "BoltzGen not found", "input_file": str(config_path)}
        }
    except KeyboardInterrupt:
        log_error("Process interrupted by user")
        if process:
            process.terminate()
            process.wait()
        return {
            "result": 130,
            "output_file": None,
            "metadata": {"error": "Interrupted", "input_file": str(config_path)}
        }
    except Exception as e:
        log_error(f"Error running BoltzGen: {e}")
        return {
            "result": 1,
            "output_file": None,
            "metadata": {"error": str(e), "input_file": str(config_path)}
        }