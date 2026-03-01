"""
BoltzGen protein design tools.

This MCP Server provides tools for designing proteins using BoltzGen:
1. boltzgen_run: Run full BoltzGen protein design pipeline (synchronous)
2. boltzgen_submit: Submit a BoltzGen job to the queue (FIFO with GPU scheduling)
3. boltzgen_check_status: Check status and results of a submitted job
4. boltzgen_queue_status: Check queue status, running jobs, and GPU availability
5. boltzgen_cancel_job: Cancel a queued or running job
6. boltzgen_configure_queue: Configure max workers and GPU settings

The tools use:
- BoltzGen for protein structure generation and optimization
- FIFO job queue with automatic GPU assignment
"""

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Annotated, Literal, Optional, List

from fastmcp import FastMCP
from loguru import logger

# Import queue functions
from jobs import (
    queue_job,
    get_queue_status,
    get_queued_job_status,
    cancel_queued_job,
    configure_queue,
    get_job_queue,
    get_resource_status,
)

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
    # Triton JIT cache needs a writable directory
    run_env.setdefault("TRITON_HOME", "/tmp")

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
            # Count output design files (PDB and CIF)
            if output_dir.exists():
                pdb_files = list(output_dir.glob("**/*.pdb"))
                cif_files = list(output_dir.glob("**/*.cif"))
                design_files = pdb_files + cif_files
                output_stats["total_designs"] = len(design_files)
                output_stats["pdb_files"] = [str(f.relative_to(output_dir)) for f in design_files[:20]]

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
) -> dict:
    """
    Submit a BoltzGen protein design job to the queue.

    Jobs are processed in FIFO order with automatic GPU assignment.
    Multiple jobs can run in parallel if multiple GPUs are configured.
    Default: 1 job at a time (configurable via boltzgen_configure_queue).

    The tool will:
    1. Validate inputs and configuration file
    2. Add job to the queue
    3. Return immediately with job_id and queue position
    4. Queue worker starts job when GPU is available

    Use boltzgen_check_status with output_dir or job_id to monitor progress.
    Use boltzgen_queue_status to see overall queue state.

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

    Note: GPU is automatically assigned from the pool. No need to specify cuda_device.

    Output: Dictionary with status='queued', job_id, queue position, and output_dir
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

        logger.info(f"Config: {config}")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Protocol: {protocol}")

        # Build args for the queue
        args = {
            "config": config,
            "output": str(output_dir),
            "protocol": protocol,
            "num_designs": num_designs,
            "budget": budget,
        }

        # Submit to queue
        script_path = str(scripts_path / "run_boltzgen.py")
        result = queue_job(
            script_path=script_path,
            args=args,
            output_dir=str(output_dir),
            job_name=f"boltzgen_{protocol}_{Path(config).stem}"
        )

        logger.info(f"=" * 80)
        logger.info(f"Job {result['job_id']} added to queue at position {result['position']}")
        logger.info(f"OUTPUT DIRECTORY: {output_dir}")
        logger.info(f"=" * 80)

        return {
            "status": result["status"],
            "job_id": result["job_id"],
            "queue_position": result["position"],
            "queue_length": result["queue_length"],
            "message": f"Job queued at position {result['position']}. Use boltzgen_check_status or boltzgen_queue_status to monitor.",
            "output_dir": str(output_dir),
            "config": config,
            "protocol": protocol,
            "num_designs": num_designs,
            "budget": budget,
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
            # Find all design files (PDB and CIF)
            pdb_files = list(output_dir.glob("**/*.pdb"))
            cif_files = list(output_dir.glob("**/*.cif"))
            design_files = pdb_files + cif_files
            stats["total_designs"] = len(design_files)
            stats["pdb_files"] = [str(f.relative_to(output_dir)) for f in design_files[:20]]

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


@boltzgen_design_mcp.tool
def boltzgen_queue_status() -> dict:
    """
    Get the current status of the job queue.

    Returns information about:
    - Number of jobs waiting in queue
    - Currently running jobs and their GPU assignments
    - Available GPUs
    - Queue configuration (max_workers, total GPUs)

    Use this to monitor overall system status and plan job submissions.

    Output: Dictionary with queue statistics and job lists
    """
    logger.info("boltzgen_queue_status called")

    try:
        result = get_queue_status()

        logger.info(f"Queue status: {result['queue_length']} queued, {result['running_count']} running")

        return result

    except Exception as e:
        logger.exception(f"Exception getting queue status: {e}")
        return {
            "status": "error",
            "error_message": str(e),
        }


@boltzgen_design_mcp.tool
def boltzgen_cancel_job(
    job_id: Annotated[str, "Job ID to cancel (from boltzgen_submit response)"],
) -> dict:
    """
    Cancel a queued or running job.

    If the job is queued, it will be removed from the queue.
    If the job is running, the process will be terminated and GPU released.

    Parameters:
    - job_id: The job ID returned from boltzgen_submit

    Output: Dictionary with cancellation result
    """
    logger.info(f"boltzgen_cancel_job called for job_id={job_id}")

    try:
        result = cancel_queued_job(job_id)

        logger.info(f"Cancel result: {result}")

        return result

    except Exception as e:
        logger.exception(f"Exception cancelling job: {e}")
        return {
            "status": "error",
            "error_message": str(e),
        }


@boltzgen_design_mcp.tool
def boltzgen_configure_queue(
    max_workers: Annotated[Optional[int], "Maximum concurrent jobs (default: 1)"] = None,
    gpu_ids: Annotated[Optional[str], "Comma-separated GPU IDs (e.g., '0,1')"] = None,
) -> dict:
    """
    Configure the job queue settings.

    Allows changing:
    - max_workers: How many jobs can run in parallel (limited by GPU count)
    - gpu_ids: Which GPUs to use for job execution

    Note: Changing these settings will reinitialize the queue.
    Running jobs will continue, but queued jobs may be affected.

    Parameters:
    - max_workers: Maximum concurrent jobs. Set to number of GPUs for full parallelism.
    - gpu_ids: Comma-separated list of GPU IDs (e.g., "0,1" for two GPUs)

    Output: Dictionary with new queue configuration
    """
    logger.info(f"boltzgen_configure_queue called: max_workers={max_workers}, gpu_ids={gpu_ids}")

    try:
        # Parse gpu_ids if provided
        gpu_list = None
        if gpu_ids:
            gpu_list = [g.strip() for g in gpu_ids.split(",")]

        result = configure_queue(max_workers=max_workers, gpu_ids=gpu_list)

        logger.info(f"Queue configured: max_workers={result['max_workers']}, gpus={result['gpu_ids']}")

        return result

    except Exception as e:
        logger.exception(f"Exception configuring queue: {e}")
        return {
            "status": "error",
            "error_message": str(e),
        }


@boltzgen_design_mcp.tool
def boltzgen_job_status(
    job_id: Annotated[str, "Job ID to check (from boltzgen_submit response)"],
) -> dict:
    """
    Get the status of a specific queued job by job_id.

    This is useful when you have the job_id but not the output_dir.
    For checking status by output_dir, use boltzgen_check_status instead.

    Parameters:
    - job_id: The job ID returned from boltzgen_submit

    Output: Dictionary with job status, queue position, and details
    """
    logger.info(f"boltzgen_job_status called for job_id={job_id}")

    try:
        result = get_queued_job_status(job_id)

        logger.info(f"Job {job_id} status: {result.get('job_status', 'unknown')}")

        return result

    except Exception as e:
        logger.exception(f"Exception getting job status: {e}")
        return {
            "status": "error",
            "error_message": str(e),
        }


@boltzgen_design_mcp.tool
def boltzgen_resource_status() -> dict:
    """
    Check resource usage and verify GPUs are freed when idle.

    Use this tool to confirm that:
    - When no jobs are running, all GPUs are available for other programs
    - The MCP server is not holding GPU/CPU/memory resources unnecessarily

    The MCP server itself does NOT use GPU memory. GPU memory is only used
    by BoltzGen subprocess workers, which release all memory when they complete.

    Output: Dictionary with:
    - is_idle: True if no jobs queued or running
    - all_gpus_free: True if all GPUs available for other programs
    - resource_usage: Detailed breakdown of jobs and GPU states
    """
    logger.info("boltzgen_resource_status called")

    try:
        result = get_resource_status()

        if result.get("is_idle") and result.get("all_gpus_free"):
            logger.info("System idle - all GPUs free for other programs")
        else:
            logger.info(f"Resource status: {result.get('message')}")

        return result

    except Exception as e:
        logger.exception(f"Exception getting resource status: {e}")
        return {
            "status": "error",
            "error_message": str(e),
        }
