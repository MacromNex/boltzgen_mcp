#!/usr/bin/env python3
"""MCP Server for BoltzGen

Provides both synchronous and asynchronous (submit) APIs for BoltzGen tools.
"""

from fastmcp import FastMCP
from pathlib import Path
from typing import Optional, List
import sys

# Setup paths
SCRIPT_DIR = Path(__file__).parent.resolve()
MCP_ROOT = SCRIPT_DIR.parent
SCRIPTS_DIR = MCP_ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

from jobs.manager import job_manager
from loguru import logger

# Create MCP server
mcp = FastMCP("boltzgen")

# ==============================================================================
# Job Management Tools (for async operations)
# ==============================================================================

@mcp.tool()
def get_job_status(job_id: str) -> dict:
    """
    Get the status of a submitted job.

    Args:
        job_id: The job ID returned from a submit_* function

    Returns:
        Dictionary with job status, timestamps, and any errors
    """
    return job_manager.get_job_status(job_id)

@mcp.tool()
def get_job_result(job_id: str) -> dict:
    """
    Get the results of a completed job.

    Args:
        job_id: The job ID of a completed job

    Returns:
        Dictionary with the job results or error if not completed
    """
    return job_manager.get_job_result(job_id)

@mcp.tool()
def get_job_log(job_id: str, tail: int = 50) -> dict:
    """
    Get log output from a running or completed job.

    Args:
        job_id: The job ID to get logs for
        tail: Number of lines from end (default: 50, use 0 for all)

    Returns:
        Dictionary with log lines and total line count
    """
    return job_manager.get_job_log(job_id, tail)

@mcp.tool()
def cancel_job(job_id: str) -> dict:
    """
    Cancel a running job.

    Args:
        job_id: The job ID to cancel

    Returns:
        Success or error message
    """
    return job_manager.cancel_job(job_id)

@mcp.tool()
def list_jobs(status: Optional[str] = None) -> dict:
    """
    List all submitted jobs.

    Args:
        status: Filter by status (pending, running, completed, failed, cancelled)

    Returns:
        List of jobs with their status
    """
    return job_manager.list_jobs(status)

# ==============================================================================
# Synchronous Tools (for fast operations < 5 min)
# ==============================================================================

@mcp.tool()
def validate_config(
    config_file: str,
    verbose: bool = False
) -> dict:
    """
    Validate a BoltzGen configuration file quickly.

    This is a fast operation that checks if a configuration file is valid
    for BoltzGen without running the full pipeline.

    Args:
        config_file: Path to the BoltzGen YAML configuration file
        verbose: Enable verbose output

    Returns:
        Dictionary with validation results
    """
    try:
        # Import the check_config functionality
        import subprocess

        cmd = [
            "mamba", "run", "-p", str(MCP_ROOT / "env"),
            "python", str(SCRIPTS_DIR / "check_config.py"),
            "--config", config_file
        ]

        if verbose:
            cmd.append("--verbose")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(MCP_ROOT)
        )

        return {
            "status": "success" if result.returncode == 0 else "error",
            "config_file": config_file,
            "valid": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }

    except FileNotFoundError:
        return {
            "status": "error",
            "error": f"Configuration file not found: {config_file}"
        }
    except Exception as e:
        logger.error(f"Config validation failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

# ==============================================================================
# Submit Tools (for long-running operations > 5 min)
# ==============================================================================

@mcp.tool()
def submit_protein_binder_design(
    config_file: str,
    output_dir: str,
    num_designs: int = 10,
    budget: int = 2,
    cuda_device: Optional[str] = None,
    master_port: Optional[int] = None,
    verbose: bool = True,
    job_name: Optional[str] = None
) -> dict:
    """
    Submit protein binder design for background processing using BoltzGen.

    This operation typically takes 5-20 minutes depending on design complexity.
    Uses the protein-anything protocol to design protein binders against a target.

    Args:
        config_file: Path to BoltzGen YAML configuration file
        output_dir: Directory to save design outputs
        num_designs: Number of designs to generate (default: 10)
        budget: Computational budget for design (default: 2)
        cuda_device: CUDA device ID (optional, auto-detected if available)
        master_port: Port for distributed training (default: 29500)
        verbose: Enable verbose logging (default: True)
        job_name: Optional name for tracking this job

    Returns:
        Dictionary with job_id for tracking. Use:
        - get_job_status(job_id) to check progress
        - get_job_result(job_id) to get results when completed
        - get_job_log(job_id) to see execution logs
    """
    script_path = str(SCRIPTS_DIR / "protein_binder_design.py")

    args = {
        "input": config_file,
        "output": output_dir,
        "num_designs": num_designs,
        "budget": budget,
        "verbose": verbose
    }

    # Add optional parameters
    if cuda_device is not None:
        args["cuda_device"] = cuda_device
    if master_port is not None:
        args["master_port"] = master_port

    return job_manager.submit_job(
        script_path=script_path,
        args=args,
        job_name=job_name or f"protein_binder_{Path(config_file).stem}"
    )

@mcp.tool()
def submit_peptide_binder_design(
    config_file: str,
    output_dir: str,
    num_designs: int = 10,
    budget: int = 2,
    alpha: Optional[float] = None,
    cuda_device: Optional[str] = None,
    master_port: Optional[int] = None,
    verbose: bool = True,
    job_name: Optional[str] = None
) -> dict:
    """
    Submit peptide binder design for background processing using BoltzGen.

    This operation typically takes 5-15 minutes depending on design complexity.
    Uses the peptide-anything protocol to design peptide binders against a target.

    Args:
        config_file: Path to BoltzGen YAML configuration file
        output_dir: Directory to save design outputs
        num_designs: Number of designs to generate (default: 10)
        budget: Computational budget for design (default: 2)
        alpha: Diversity parameter (0.0=quality focused, 1.0=diversity focused)
        cuda_device: CUDA device ID (optional, auto-detected if available)
        master_port: Port for distributed training (default: 29500)
        verbose: Enable verbose logging (default: True)
        job_name: Optional name for tracking this job

    Returns:
        Dictionary with job_id for tracking. Use:
        - get_job_status(job_id) to check progress
        - get_job_result(job_id) to get results when completed
        - get_job_log(job_id) to see execution logs
    """
    script_path = str(SCRIPTS_DIR / "peptide_binder_design.py")

    args = {
        "input": config_file,
        "output": output_dir,
        "num_designs": num_designs,
        "budget": budget,
        "verbose": verbose
    }

    # Add optional parameters
    if alpha is not None:
        args["alpha"] = alpha
    if cuda_device is not None:
        args["cuda_device"] = cuda_device
    if master_port is not None:
        args["master_port"] = master_port

    return job_manager.submit_job(
        script_path=script_path,
        args=args,
        job_name=job_name or f"peptide_binder_{Path(config_file).stem}"
    )

@mcp.tool()
def submit_generic_boltzgen(
    config_file: str,
    output_dir: str,
    protocol: str = "protein-anything",
    num_designs: int = 10,
    budget: int = 2,
    cuda_device: Optional[str] = None,
    master_port: Optional[int] = None,
    verbose: bool = True,
    job_name: Optional[str] = None
) -> dict:
    """
    Submit generic BoltzGen job for background processing.

    This is a flexible tool that can run any BoltzGen protocol.
    Runtime varies based on protocol and complexity (5-30 minutes typical).

    Args:
        config_file: Path to BoltzGen YAML configuration file
        output_dir: Directory to save outputs
        protocol: BoltzGen protocol (protein-anything, peptide-anything, etc.)
        num_designs: Number of designs to generate (default: 10)
        budget: Computational budget for design (default: 2)
        cuda_device: CUDA device ID (optional, auto-detected if available)
        master_port: Port for distributed training (default: 29500)
        verbose: Enable verbose logging (default: True)
        job_name: Optional name for tracking this job

    Returns:
        Dictionary with job_id for tracking. Use:
        - get_job_status(job_id) to check progress
        - get_job_result(job_id) to get results when completed
        - get_job_log(job_id) to see execution logs
    """
    script_path = str(SCRIPTS_DIR / "run_boltzgen.py")

    args = {
        "config": config_file,
        "output": output_dir,
        "protocol": protocol,
        "num_designs": num_designs,
        "budget": budget,
        "verbose": verbose
    }

    # Add optional parameters
    if cuda_device is not None:
        args["cuda_device"] = cuda_device
    if master_port is not None:
        args["master_port"] = master_port

    return job_manager.submit_job(
        script_path=script_path,
        args=args,
        job_name=job_name or f"boltzgen_{protocol}_{Path(config_file).stem}"
    )

# ==============================================================================
# Batch Processing Tools
# ==============================================================================

@mcp.tool()
def submit_batch_protein_design(
    config_files: List[str],
    output_base_dir: str,
    num_designs: int = 10,
    budget: int = 2,
    cuda_device: Optional[str] = None,
    job_name: Optional[str] = None
) -> dict:
    """
    Submit batch protein binder design for multiple configuration files.

    Processes multiple protein targets in sequence. Each design typically
    takes 5-20 minutes, so total runtime = num_configs * avg_time_per_design.

    Args:
        config_files: List of BoltzGen YAML configuration files to process
        output_base_dir: Base directory for outputs (subdirs created per config)
        num_designs: Number of designs per target (default: 10)
        budget: Computational budget per design (default: 2)
        cuda_device: CUDA device ID (optional, auto-detected if available)
        job_name: Optional name for tracking the batch job

    Returns:
        Dictionary with job_id for tracking the batch job
    """
    # Create a temporary script for batch processing
    import tempfile
    import textwrap

    # Create batch processing script
    batch_script_content = textwrap.dedent(f'''
    #!/usr/bin/env python3
    """Batch protein binder design script"""
    import sys
    from pathlib import Path
    sys.path.insert(0, "{SCRIPTS_DIR}")
    from protein_binder_design import run_protein_binder_design

    config_files = {config_files!r}
    output_base_dir = "{output_base_dir}"
    num_designs = {num_designs}
    budget = {budget}
    cuda_device = {cuda_device!r}

    results = []
    for config_file in config_files:
        config_name = Path(config_file).stem
        output_dir = Path(output_base_dir) / f"{{config_name}}_protein_design"

        print(f"Processing {{config_file}} -> {{output_dir}}")

        result = run_protein_binder_design(
            input_file=config_file,
            output_file=str(output_dir),
            num_designs=num_designs,
            budget=budget,
            cuda_device=cuda_device,
            verbose=True
        )

        results.append({{
            "config_file": config_file,
            "output_dir": str(output_dir),
            "result": result
        }})

        print(f"Completed {{config_file}}: {{result}}")

    print(f"Batch processing completed. Results: {{results}}")
    ''')

    # Write temporary batch script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(batch_script_content)
        batch_script_path = f.name

    return job_manager.submit_job(
        script_path=batch_script_path,
        args={},  # Arguments are embedded in the script
        job_name=job_name or f"batch_protein_{len(config_files)}_targets"
    )

# ==============================================================================
# Entry Point
# ==============================================================================

if __name__ == "__main__":
    mcp.run()