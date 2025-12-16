"""
BoltzGen protein design tools.

This MCP Server provides tools for designing proteins using BoltzGen:
1. boltzgen_run: Run full BoltzGen protein design pipeline (synchronous)
2. boltzgen_submit: Submit a BoltzGen job asynchronously (returns immediately)
3. boltzgen_check_status: Check status and results of a submitted job

The tools use:
- BoltzGen for protein structure generation and optimization
"""

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Annotated, Literal, Optional

from fastmcp import FastMCP
from loguru import logger

# MCP server instance
boltzgen_design_mcp = FastMCP(name="boltzgen_design")

# BoltzGen protocols
BOLTZGEN_PROTOCOLS = Literal[
    "protein-anything",
    "peptide-anything",
    "protein-small_molecule",
    "nanobody-anything",
    "antibody-anything",
]

PROTOCOL_DESCRIPTIONS = {
    "protein-anything": "General protein binder design (default)",
    "peptide-anything": "Peptide binder design (filters cysteines, lower diversity)",
    "protein-small_molecule": "Protein-small molecule interaction design (includes affinity metrics)",
    "nanobody-anything": "Nanobody binder design (filters cysteines)",
    "antibody-anything": "Antibody binder design (filters cysteines)",
}


def _validate_protocol(protocol: str) -> None:
    """Validate that the protocol is one of the supported BoltzGen protocols."""
    valid_protocols = ["protein-anything", "peptide-anything", "protein-small_molecule",
                      "nanobody-anything", "antibody-anything"]
    if protocol not in valid_protocols:
        raise ValueError(
            f"Invalid protocol: {protocol}. Must be one of: {', '.join(valid_protocols)}\n"
            + "\n".join([f"  - {k}: {v}" for k, v in PROTOCOL_DESCRIPTIONS.items()])
        )


def _get_boltzgen_scripts_path() -> Path:
    """Get the BoltzGen scripts path."""
    # src/tools/boltzgen_design.py -> src -> boltzgen_mcp -> scripts
    src_dir = Path(__file__).parent.parent.absolute()
    scripts_path = src_dir.parent / "scripts"

    if not scripts_path.exists():
        logger.error(f"BoltzGen scripts not found at {scripts_path}")
        raise FileNotFoundError(
            f"BoltzGen scripts not found at {scripts_path}. "
            "Please ensure the scripts directory exists."
        )
    return scripts_path


def _resolve_path(path: Optional[str]) -> Optional[str]:
    """Resolve a path to absolute."""
    if path is None:
        return None
    return str(Path(path).resolve())


def _log_stream(stream, logs: list[str], prefix: str = ""):
    """Collect output from a stream and print in real-time."""
    for line in iter(stream.readline, ""):
        line = line.rstrip()
        if line:
            logs.append(line)
            logger.info(f"{prefix}{line}")


def _run_command(
    cmd: list[str],
    cuda_device: Optional[str] = None,
    cwd: Optional[str] = None,
) -> dict:
    """Run a command with proper environment setup."""
    run_env = os.environ.copy()
    if cuda_device is not None:
        run_env["CUDA_VISIBLE_DEVICES"] = cuda_device
    run_env["PYTHONUNBUFFERED"] = "1"

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    logger.debug(f"Executing command: {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=run_env,
        cwd=cwd,
        bufsize=1,
    )

    stdout_thread = threading.Thread(
        target=_log_stream,
        args=(process.stdout, stdout_lines, "[BoltzGen] "),
    )
    stderr_thread = threading.Thread(
        target=_log_stream,
        args=(process.stderr, stderr_lines, "[BoltzGen stderr] "),
    )

    stdout_thread.start()
    stderr_thread.start()

    process.wait()
    stdout_thread.join()
    stderr_thread.join()

    if process.stdout:
        process.stdout.close()
    if process.stderr:
        process.stderr.close()

    logger.debug(f"Command completed with return code: {process.returncode}")

    return {
        "success": process.returncode == 0,
        "return_code": process.returncode,
        "stdout": "\n".join(stdout_lines),
        "stderr": "\n".join(stderr_lines),
    }


@boltzgen_design_mcp.tool
def boltzgen_run(
    config: Annotated[str, "Path to BoltzGen YAML configuration file"],
    output: Annotated[str, "Output directory path"],
    protocol: Annotated[
        BOLTZGEN_PROTOCOLS,
        "BoltzGen protocol: protein-anything (default), peptide-anything, protein-small_molecule, nanobody-anything, or antibody-anything"
    ] = "protein-anything",
    num_designs: Annotated[int, "Number of designs to generate"] = 10,
    budget: Annotated[int, "Budget parameter for BoltzGen"] = 2,
    cuda_device: Annotated[Optional[str], "CUDA device ID (e.g., '0' or '1')"] = None,
) -> dict:
    """
    Run BoltzGen protein design pipeline synchronously.

    This tool runs the complete BoltzGen workflow to generate protein structures.
    It waits for completion and returns full results.

    BoltzGen generates protein structures using:
    - Structure prediction and optimization with Boltz models
    - Multiple sampling strategies for diverse designs
    - Quality assessment and ranking

    Configuration File Format (YAML):
    The config file should contain BoltzGen-specific parameters for the target
    protein structure generation. See BoltzGen documentation for details.

    Available Protocols:
    - protein-anything: General protein binder design (default)
    - peptide-anything: Peptide binder design (filters cysteines, lower diversity)
    - protein-small_molecule: Protein-small molecule interaction design (includes affinity metrics)
    - nanobody-anything: Nanobody binder design (filters cysteines)
    - antibody-anything: Antibody binder design (filters cysteines)

    Parameters:
    - config: Path to YAML configuration file with BoltzGen settings
    - output: Output directory where results will be saved
    - protocol: BoltzGen protocol to use (see Available Protocols above)
    - num_designs: Number of protein designs to generate
    - budget: Computational budget parameter
    - cuda_device: Optional GPU device ID (e.g., '0', '1')

    Output: Dictionary with run status, output paths, and statistics
    """
    logger.info(f"boltzgen_run called with config={config}, output={output}")

    # Validate protocol
    _validate_protocol(protocol)

    try:
        scripts_path = _get_boltzgen_scripts_path()

        # Resolve paths
        config = _resolve_path(config)
        output = _resolve_path(output)

        logger.info(f"=" * 80)
        logger.info(f"OUTPUT DIRECTORY: {output}")
        logger.info(f"=" * 80)

        # Validate config file exists
        if not Path(config).exists():
            logger.error(f"Config file not found: {config}")
            raise FileNotFoundError(f"Config file not found: {config}")

        # Create output directory
        output_dir = Path(output)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Config: {config}")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Protocol: {protocol}")
        logger.info(f"Num designs: {num_designs}")
        logger.info(f"Budget: {budget}")

        # Build command using the run_boltzgen.py script
        cmd = [
            sys.executable,
            str(scripts_path / "run_boltzgen.py"),
            "--config", config,
            "--output", str(output_dir),
            "--protocol", protocol,
            "--num_designs", str(num_designs),
            "--budget", str(budget),
        ]

        if cuda_device is not None:
            cmd.extend(["--cuda_device", cuda_device])
            logger.info(f"Running BoltzGen on GPU {cuda_device}")
        else:
            logger.info("Running BoltzGen (GPU auto-select)")

        # Run design
        result = _run_command(cmd, cuda_device=cuda_device, cwd=str(scripts_path))

        # Collect output statistics
        output_stats = {
            "total_designs": 0,
            "pdb_files": [],
        }

        if result["success"]:
            # Count output PDB files
            if output_dir.exists():
                pdb_files = list(output_dir.glob("**/*.pdb"))
                output_stats["total_designs"] = len(pdb_files)
                output_stats["pdb_files"] = [str(f.relative_to(output_dir)) for f in pdb_files[:20]]

            logger.info(f"=" * 80)
            logger.info(f"Design completed. Generated {output_stats['total_designs']} designs")
            logger.info(f"OUTPUT DIRECTORY: {output_dir}")
            logger.info(f"=" * 80)
        else:
            logger.error(f"Design failed with return code {result['return_code']}")
            logger.error(f"OUTPUT DIRECTORY: {output_dir}")

        return {
            "status": "success" if result["success"] else "error",
            "config": config,
            "output_dir": str(output_dir),
            "protocol": protocol,
            "num_designs": num_designs,
            "budget": budget,
            "cuda_device": cuda_device,
            "statistics": output_stats,
            "return_code": result["return_code"],
            "stdout_preview": result["stdout"][-3000:] if len(result["stdout"]) > 3000 else result["stdout"],
            "stderr_preview": result["stderr"][-2000:] if len(result["stderr"]) > 2000 else result["stderr"],
        }

    except Exception as e:
        logger.exception(f"Exception during BoltzGen run: {e}")
        return {
            "status": "error",
            "error_message": str(e),
            "config": config,
        }


@boltzgen_design_mcp.tool
def boltzgen_submit(
    config: Annotated[str, "Path to BoltzGen YAML configuration file"],
    output: Annotated[str, "Output directory path"],
    protocol: Annotated[
        BOLTZGEN_PROTOCOLS,
        "BoltzGen protocol: protein-anything (default), peptide-anything, protein-small_molecule, nanobody-anything, or antibody-anything"
    ] = "protein-anything",
    num_designs: Annotated[int, "Number of designs to generate"] = 10,
    budget: Annotated[int, "Budget parameter for BoltzGen"] = 2,
    cuda_device: Annotated[Optional[str], "CUDA device ID (e.g., '0' or '1')"] = None,
) -> dict:
    """
    Submit a BoltzGen protein design job asynchronously.

    This tool submits a BoltzGen job and returns immediately with a 'submitted' status.
    The job runs in the background and results can be queried using boltzgen_check_status.

    The tool will:
    1. Validate inputs and configuration file
    2. Launch the BoltzGen process in the background
    3. Return immediately with submission status and output directory
    4. Job continues running independently

    Use boltzgen_check_status with the returned output_dir to monitor progress.

    Available Protocols:
    - protein-anything: General protein binder design (default)
    - peptide-anything: Peptide binder design (filters cysteines, lower diversity)
    - protein-small_molecule: Protein-small molecule interaction design (includes affinity metrics)
    - nanobody-anything: Nanobody binder design (filters cysteines)
    - antibody-anything: Antibody binder design (filters cysteines)

    Parameters:
    - config: Path to YAML configuration file with BoltzGen settings
    - output: Output directory where results will be saved
    - protocol: BoltzGen protocol to use (see Available Protocols above)
    - num_designs: Number of protein designs to generate
    - budget: Computational budget parameter
    - cuda_device: Optional GPU device ID (e.g., '0', '1')

    Output: Dictionary with status='submitted', output_dir, and job info
    """
    logger.info(f"boltzgen_submit called with config={config}, output={output}")

    # Validate protocol
    _validate_protocol(protocol)

    try:
        scripts_path = _get_boltzgen_scripts_path()

        # Resolve paths
        config = _resolve_path(config)
        output = _resolve_path(output)

        logger.info(f"=" * 80)
        logger.info(f"OUTPUT DIRECTORY: {output}")
        logger.info(f"=" * 80)

        # Validate config file exists
        if not Path(config).exists():
            logger.error(f"Config file not found: {config}")
            raise FileNotFoundError(f"Config file not found: {config}")

        # Create output directory
        output_dir = Path(output)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save job info
        job_info = {
            "config": config,
            "output_dir": str(output_dir),
            "protocol": protocol,
            "num_designs": num_designs,
            "budget": budget,
            "cuda_device": cuda_device,
            "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        job_info_path = output_dir / "job_info.json"
        with open(job_info_path, 'w') as f:
            json.dump(job_info, f, indent=2)

        logger.info(f"Config: {config}")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Protocol: {protocol}")

        # Build command using the run_boltzgen.py script
        cmd = [
            sys.executable,
            str(scripts_path / "run_boltzgen.py"),
            "--config", config,
            "--output", str(output_dir),
            "--protocol", protocol,
            "--num_designs", str(num_designs),
            "--budget", str(budget),
        ]

        if cuda_device is not None:
            cmd.extend(["--cuda_device", cuda_device])

        # Setup environment
        run_env = os.environ.copy()
        if cuda_device is not None:
            run_env["CUDA_VISIBLE_DEVICES"] = cuda_device
        run_env["PYTHONUNBUFFERED"] = "1"

        # Create log file for the background process
        log_file = output_dir / "boltzgen_run.log"

        logger.info(f"Submitting BoltzGen job" + (f" on GPU {cuda_device}" if cuda_device else ""))
        logger.debug(f"Command: {' '.join(cmd)}")
        logger.info(f"Log file: {log_file}")

        # Launch process in background
        with open(log_file, 'w') as log_f:
            process = subprocess.Popen(
                cmd,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                env=run_env,
                cwd=str(scripts_path),
                start_new_session=True,  # Detach from parent
            )

        logger.info(f"=" * 80)
        logger.info(f"Job submitted successfully. PID: {process.pid}")
        logger.info(f"OUTPUT DIRECTORY: {output_dir}")
        logger.info(f"LOG FILE: {log_file}")
        logger.info(f"=" * 80)

        # Update job info with PID
        job_info["pid"] = process.pid
        with open(job_info_path, 'w') as f:
            json.dump(job_info, f, indent=2)

        return {
            "status": "submitted",
            "message": "BoltzGen job submitted successfully. Use boltzgen_check_status to monitor progress.",
            "output_dir": str(output_dir),
            "config": config,
            "protocol": protocol,
            "num_designs": num_designs,
            "budget": budget,
            "cuda_device": cuda_device,
            "log_file": str(log_file),
            "job_info_file": str(job_info_path),
            "pid": process.pid,
        }

    except Exception as e:
        logger.exception(f"Exception during job submission: {e}")
        return {
            "status": "error",
            "error_message": str(e),
        }


@boltzgen_design_mcp.tool
def boltzgen_check_status(
    output_dir: Annotated[str, "Path to BoltzGen output directory"],
) -> dict:
    """
    Check the status of a BoltzGen design run.

    This tool inspects an existing output directory to report:
    - Job status: running, completed, failed, or unknown
    - Number of generated designs (PDB files)
    - List of output files
    - Job configuration and parameters
    - Result summary (if job is finished)

    The tool determines job status by:
    1. Checking if the log file exists and parsing it for completion markers
    2. Detecting success/failure indicators in the log
    3. Checking file modification times to detect stalled jobs
    4. Providing detailed summary when job is complete

    Use this to monitor long-running design jobs or inspect completed runs.

    Parameters:
    - output_dir: Path to BoltzGen output directory

    Output: Dictionary with job status, design statistics, and summary if finished
    """
    logger.info(f"boltzgen_check_status called for: {output_dir}")

    try:
        output_dir = Path(output_dir).resolve()

        logger.info(f"=" * 80)
        logger.info(f"CHECKING OUTPUT DIRECTORY: {output_dir}")
        logger.info(f"=" * 80)

        if not output_dir.exists():
            return {
                "status": "error",
                "error_message": f"Output directory not found: {output_dir}",
            }

        # Load job info if available
        job_info = None
        job_info_path = output_dir / "job_info.json"
        if job_info_path.exists():
            with open(job_info_path) as f:
                job_info = json.load(f)

        # Check for log file and determine job status
        log_file = output_dir / "boltzgen_run.log"
        job_status = "unknown"
        log_tail = []
        error_messages = []

        if log_file.exists():
            # Check file modification time to detect if still running
            log_mtime = log_file.stat().st_mtime
            current_time = time.time()
            time_since_update = current_time - log_mtime

            # Read log file to check for completion markers
            try:
                with open(log_file, 'r') as f:
                    log_lines = f.readlines()

                # Get last 50 lines for inspection
                log_tail = [line.strip() for line in log_lines[-50:] if line.strip()]

                # Look for completion/error markers in the log
                log_content_lower = ''.join(log_lines).lower()

                # Check for completion indicators
                has_completion = any(marker in log_content_lower for marker in [
                    'boltzgen completed successfully',
                    'design completed',
                    'all designs completed',
                    'finished',
                ])

                # Check for error indicators
                has_error = any(marker in log_content_lower for marker in [
                    'error:',
                    'exception:',
                    'traceback',
                    'failed:',
                    'fatal',
                ])

                # Extract error messages if present
                if has_error:
                    for line in log_lines[-100:]:
                        line_lower = line.lower()
                        if any(err in line_lower for err in ['error:', 'exception:', 'failed:', 'fatal:']):
                            error_messages.append(line.strip())

                # Determine status
                if has_completion and not has_error:
                    job_status = "completed"
                elif has_error:
                    job_status = "failed"
                elif time_since_update < 300:  # Updated within last 5 minutes
                    job_status = "running"
                elif time_since_update < 3600:  # Updated within last hour
                    job_status = "possibly_running"
                else:
                    job_status = "stalled_or_completed"

            except Exception as e:
                logger.warning(f"Could not parse log file: {e}")
                job_status = "unknown"
        else:
            job_status = "not_started"

        # Count output files
        stats = {
            "total_designs": 0,
            "pdb_files": [],
            "other_files": [],
        }

        if output_dir.exists():
            # Find all PDB files
            pdb_files = list(output_dir.glob("**/*.pdb"))
            stats["total_designs"] = len(pdb_files)
            stats["pdb_files"] = [str(f.relative_to(output_dir)) for f in pdb_files[:20]]

            # Find other relevant files
            for pattern in ["*.json", "*.csv", "*.txt"]:
                other_files = list(output_dir.glob(pattern))
                stats["other_files"].extend([str(f.relative_to(output_dir)) for f in other_files])

        # Build response
        response = {
            "status": "success",
            "job_status": job_status,
            "output_dir": str(output_dir),
            "statistics": stats,
            "job_info": job_info,
            "log_file": str(log_file) if log_file.exists() else None,
        }

        # Add summary if job is finished (completed or failed)
        if job_status in ["completed", "failed"]:
            summary = _generate_job_summary(
                job_status=job_status,
                stats=stats,
                job_info=job_info,
                log_tail=log_tail[-20:],
                error_messages=error_messages[-10:],
            )
            response["summary"] = summary

        logger.info(f"=" * 80)
        logger.info(f"Job status: {job_status}")
        logger.info(f"Total designs: {stats['total_designs']}")
        logger.info(f"OUTPUT DIRECTORY: {output_dir}")
        logger.info(f"=" * 80)

        return response

    except Exception as e:
        logger.exception(f"Exception checking status: {e}")
        return {
            "status": "error",
            "error_message": str(e),
            "output_dir": str(output_dir),
        }


def _generate_job_summary(
    job_status: str,
    stats: dict,
    job_info: Optional[dict],
    log_tail: list[str],
    error_messages: list[str],
) -> dict:
    """Generate a comprehensive summary for completed/failed jobs."""
    summary = {
        "job_status": job_status,
        "completion_status": "Success" if job_status == "completed" else "Failed",
    }

    # Add job information
    if job_info:
        summary["job_config"] = {
            "config": job_info.get("config"),
            "protocol": job_info.get("protocol"),
            "num_designs": job_info.get("num_designs"),
            "budget": job_info.get("budget"),
            "cuda_device": job_info.get("cuda_device"),
            "submitted_at": job_info.get("submitted_at"),
        }

    # Add results summary
    total_designs = stats["total_designs"]
    summary["results"] = {
        "total_designs": total_designs,
        "pdb_files": stats["pdb_files"],
    }

    # Add message based on status
    if job_status == "completed":
        if total_designs > 0:
            summary["message"] = f"BoltzGen completed successfully with {total_designs} design(s) generated."
        else:
            summary["message"] = "BoltzGen completed but no designs were generated."
    elif job_status == "failed":
        summary["message"] = "BoltzGen job failed. Check error messages and log file for details."
        if error_messages:
            summary["recent_errors"] = error_messages

    # Add log tail
    if log_tail:
        summary["log_tail"] = log_tail

    return summary
