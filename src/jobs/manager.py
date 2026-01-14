"""Job management for long-running tasks.

This module provides two job execution modes:
1. Direct execution (original JobManager) - runs jobs immediately in threads
2. Queue-based execution (JobQueue) - FIFO queue with GPU-aware scheduling

For resource-intensive GPU tasks like BoltzGen, use the queue-based execution
to prevent GPU contention and manage concurrency.
"""

import uuid
import json
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from loguru import logger

from .queue import get_job_queue, JobQueue

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobManager:
    """Manages asynchronous job execution."""

    def __init__(self, jobs_dir: Path = None):
        self.jobs_dir = jobs_dir or Path(__file__).parent.parent.parent / "jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._running_jobs: Dict[str, subprocess.Popen] = {}

    def submit_job(
        self,
        script_path: str,
        args: Dict[str, Any],
        job_name: str = None
    ) -> Dict[str, Any]:
        """Submit a new job for background execution.

        Args:
            script_path: Path to the script to run
            args: Arguments to pass to the script
            job_name: Optional name for the job

        Returns:
            Dict with job_id and status
        """
        job_id = str(uuid.uuid4())[:8]
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        # Save job metadata
        metadata = {
            "job_id": job_id,
            "job_name": job_name or f"job_{job_id}",
            "script": script_path,
            "args": args,
            "status": JobStatus.PENDING.value,
            "submitted_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "error": None
        }

        self._save_metadata(job_id, metadata)

        # Start job in background
        self._start_job(job_id, script_path, args, job_dir)

        return {
            "status": "submitted",
            "job_id": job_id,
            "message": f"Job submitted. Use get_job_status('{job_id}') to check progress."
        }

    def _start_job(self, job_id: str, script_path: str, args: Dict, job_dir: Path):
        """Start job execution in background thread."""
        def run_job():
            metadata = self._load_metadata(job_id)
            metadata["status"] = JobStatus.RUNNING.value
            metadata["started_at"] = datetime.now().isoformat()
            self._save_metadata(job_id, metadata)

            try:
                # Build command
                cmd = ["mamba", "run", "-p", str(Path(__file__).parent.parent.parent / "env"), "python", script_path]
                for key, value in args.items():
                    if value is not None:
                        # Handle different argument formats
                        if key == "input":
                            cmd.extend(["--input", str(value)])
                        elif key == "output":
                            cmd.extend(["--output", str(value)])
                        elif key == "output_dir":
                            cmd.extend(["--output", str(value)])
                        elif key == "config":
                            cmd.extend(["--config", str(value)])
                        elif key == "verbose":
                            # verbose is a flag, only add if True
                            if value:
                                cmd.append("-v")
                        elif isinstance(value, bool):
                            # Handle other boolean flags - only add if True
                            if value:
                                cmd.append(f"--{key}")
                        else:
                            cmd.extend([f"--{key}", str(value)])

                # Run script
                log_file = job_dir / "job.log"
                with open(log_file, 'w') as log:
                    process = subprocess.Popen(
                        cmd,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        cwd=str(Path(script_path).parent.parent)
                    )
                    self._running_jobs[job_id] = process
                    process.wait()

                # Update status
                if process.returncode == 0:
                    metadata["status"] = JobStatus.COMPLETED.value
                else:
                    metadata["status"] = JobStatus.FAILED.value
                    metadata["error"] = f"Process exited with code {process.returncode}"

            except Exception as e:
                metadata["status"] = JobStatus.FAILED.value
                metadata["error"] = str(e)
                logger.error(f"Job {job_id} failed: {e}")

            finally:
                metadata["completed_at"] = datetime.now().isoformat()
                self._save_metadata(job_id, metadata)
                self._running_jobs.pop(job_id, None)

        thread = threading.Thread(target=run_job, daemon=True)
        thread.start()

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a submitted job."""
        metadata = self._load_metadata(job_id)
        if not metadata:
            return {"status": "error", "error": f"Job {job_id} not found"}

        result = {
            "job_id": job_id,
            "job_name": metadata.get("job_name"),
            "status": metadata["status"],
            "submitted_at": metadata.get("submitted_at"),
            "started_at": metadata.get("started_at"),
            "completed_at": metadata.get("completed_at")
        }

        if metadata["status"] == JobStatus.FAILED.value:
            result["error"] = metadata.get("error")

        return result

    def get_job_result(self, job_id: str) -> Dict[str, Any]:
        """Get results of a completed job."""
        metadata = self._load_metadata(job_id)
        if not metadata:
            return {"status": "error", "error": f"Job {job_id} not found"}

        if metadata["status"] != JobStatus.COMPLETED.value:
            return {
                "status": "error",
                "error": f"Job not completed. Current status: {metadata['status']}"
            }

        # Load output - for BoltzGen jobs, check if output directory was created
        job_dir = self.jobs_dir / job_id
        output_dir = metadata.get("args", {}).get("output") or metadata.get("args", {}).get("output_dir")

        result = {
            "status": "success",
            "job_id": job_id,
            "job_name": metadata.get("job_name"),
            "script": metadata.get("script"),
            "args": metadata.get("args"),
            "output_directory": output_dir
        }

        # Check if output directory exists and has files
        if output_dir and Path(output_dir).exists():
            output_files = list(Path(output_dir).glob("**/*"))
            result["output_files"] = [str(f) for f in output_files if f.is_file()]
            result["output_file_count"] = len(result["output_files"])

        return result

    def get_job_log(self, job_id: str, tail: int = 50) -> Dict[str, Any]:
        """Get log output from a job."""
        job_dir = self.jobs_dir / job_id
        log_file = job_dir / "job.log"

        if not log_file.exists():
            return {"status": "error", "error": f"Log not found for job {job_id}"}

        with open(log_file) as f:
            lines = f.readlines()

        return {
            "status": "success",
            "job_id": job_id,
            "log_lines": lines[-tail:] if tail else lines,
            "total_lines": len(lines)
        }

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a running job."""
        if job_id in self._running_jobs:
            self._running_jobs[job_id].terminate()
            metadata = self._load_metadata(job_id)
            metadata["status"] = JobStatus.CANCELLED.value
            metadata["completed_at"] = datetime.now().isoformat()
            self._save_metadata(job_id, metadata)
            return {"status": "success", "message": f"Job {job_id} cancelled"}

        return {"status": "error", "error": f"Job {job_id} not running"}

    def list_jobs(self, status: Optional[str] = None) -> Dict[str, Any]:
        """List all jobs, optionally filtered by status."""
        jobs = []
        for job_dir in self.jobs_dir.iterdir():
            if job_dir.is_dir():
                metadata = self._load_metadata(job_dir.name)
                if metadata:
                    if status is None or metadata["status"] == status:
                        jobs.append({
                            "job_id": metadata["job_id"],
                            "job_name": metadata.get("job_name"),
                            "status": metadata["status"],
                            "submitted_at": metadata.get("submitted_at"),
                            "script": metadata.get("script")
                        })

        # Sort by submission time (most recent first)
        jobs.sort(key=lambda x: x.get("submitted_at", ""), reverse=True)

        return {"status": "success", "jobs": jobs, "total": len(jobs)}

    def _save_metadata(self, job_id: str, metadata: Dict):
        """Save job metadata to disk."""
        meta_file = self.jobs_dir / job_id / "metadata.json"
        meta_file.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_file, 'w') as f:
            json.dump(metadata, f, indent=2)

    def _load_metadata(self, job_id: str) -> Optional[Dict]:
        """Load job metadata from disk."""
        meta_file = self.jobs_dir / job_id / "metadata.json"
        if meta_file.exists():
            with open(meta_file) as f:
                return json.load(f)
        return None

# Global job manager instance
job_manager = JobManager()


# Queue-related helper functions for easy access
def queue_job(
    script_path: str,
    args: Dict[str, Any],
    output_dir: str,
    job_name: str = None
) -> Dict[str, Any]:
    """Submit a job to the queue (FIFO with GPU scheduling).

    This is the recommended way to submit GPU-intensive jobs like BoltzGen.
    Jobs are queued and executed in order with automatic GPU assignment.

    Args:
        script_path: Path to the script to run
        args: Arguments to pass to the script
        output_dir: Directory for job output
        job_name: Optional name for the job

    Returns:
        Dict with job_id, status, and queue position
    """
    queue = get_job_queue()
    return queue.submit(script_path, args, output_dir, job_name)


def get_queue_status() -> Dict[str, Any]:
    """Get the current queue status.

    Returns:
        Dict with queue length, running jobs, and GPU status
    """
    queue = get_job_queue()
    return queue.get_queue_status()


def get_queued_job_status(job_id: str) -> Dict[str, Any]:
    """Get status of a job submitted to the queue.

    Args:
        job_id: ID of the job

    Returns:
        Dict with job status and details
    """
    queue = get_job_queue()
    return queue.get_job_status(job_id)


def cancel_queued_job(job_id: str) -> Dict[str, Any]:
    """Cancel a queued or running job.

    Args:
        job_id: ID of the job to cancel

    Returns:
        Dict with cancellation result
    """
    queue = get_job_queue()
    return queue.cancel_job(job_id)


def configure_queue(max_workers: int = None, gpu_ids: list = None) -> Dict[str, Any]:
    """Configure and reinitialize the job queue.

    Args:
        max_workers: Maximum concurrent jobs
        gpu_ids: List of GPU IDs to use

    Returns:
        Dict with new queue configuration
    """
    queue = get_job_queue(max_workers=max_workers, gpu_ids=gpu_ids, reinitialize=True)
    return {
        "status": "success",
        "max_workers": queue.max_workers,
        "gpu_ids": queue.gpu_pool.gpu_ids,
        "message": "Queue reconfigured successfully"
    }


def get_resource_status() -> Dict[str, Any]:
    """Get current resource usage status.

    Use this to verify that GPUs are freed when no jobs are running.
    When the queue is idle, all GPUs should be available for other programs.

    Returns:
        Dict with resource usage information including:
        - is_idle: True if no jobs queued or running
        - all_gpus_free: True if all GPUs are available
        - resource_usage: Detailed counts of jobs and GPU states
    """
    queue = get_job_queue()
    return queue.get_resource_status()