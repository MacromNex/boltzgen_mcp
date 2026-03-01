"""GPU-aware job queue for BoltzGen.

Provides FIFO job scheduling with automatic GPU assignment.
Supports configurable concurrency for multi-GPU systems.

Resource Management:
- The MCP server itself does NOT hold GPU memory
- GPU memory is only used by subprocess workers (BoltzGen processes)
- When a job completes, its subprocess terminates and ALL GPU memory is freed
- The queue uses adaptive polling (longer sleep when idle) to minimize CPU usage
- Completed job metadata is cleaned from memory after a configurable period
- Jobs are tracked via lightweight Python objects, not GPU tensors
"""

import json
import os
import subprocess
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from loguru import logger


def detect_gpus() -> list[str]:
    """Auto-detect available NVIDIA GPUs using nvidia-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            gpu_ids = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
            if gpu_ids:
                logger.info(f"Auto-detected GPUs: {gpu_ids}")
                return gpu_ids
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fallback: assume single GPU
    logger.warning("Could not detect GPUs, defaulting to ['0']")
    return ["0"]


class GPUPool:
    """Manages GPU allocation for jobs.

    Thread-safe pool that tracks which GPUs are available and in use.
    """

    def __init__(self, gpu_ids: list[str] = None):
        """Initialize GPU pool.

        Args:
            gpu_ids: List of GPU IDs (e.g., ["0", "1"]). Auto-detects if None.
        """
        self.gpu_ids = gpu_ids or detect_gpus()
        self._available: set[str] = set(self.gpu_ids)
        self._in_use: dict[str, str] = {}  # gpu_id -> job_id
        self._lock = threading.Lock()
        logger.info(f"GPUPool initialized with GPUs: {self.gpu_ids}")

    def acquire(self, job_id: str) -> Optional[str]:
        """Acquire a free GPU for a job.

        Args:
            job_id: ID of the job requesting a GPU

        Returns:
            GPU ID if available, None if all GPUs are busy
        """
        with self._lock:
            if not self._available:
                return None
            gpu_id = self._available.pop()
            self._in_use[gpu_id] = job_id
            logger.debug(f"GPU {gpu_id} acquired by job {job_id}")
            return gpu_id

    def release(self, gpu_id: str) -> None:
        """Release a GPU back to the pool.

        Args:
            gpu_id: ID of the GPU to release
        """
        with self._lock:
            if gpu_id in self._in_use:
                job_id = self._in_use.pop(gpu_id)
                self._available.add(gpu_id)
                logger.debug(f"GPU {gpu_id} released by job {job_id}")

    def available_count(self) -> int:
        """Return number of available GPUs."""
        with self._lock:
            return len(self._available)

    def available_gpus(self) -> list[str]:
        """Return list of available GPU IDs."""
        with self._lock:
            return list(self._available)

    def in_use_gpus(self) -> dict[str, str]:
        """Return dict of GPU ID -> job ID for in-use GPUs."""
        with self._lock:
            return dict(self._in_use)

    def total_gpus(self) -> int:
        """Return total number of GPUs in pool."""
        return len(self.gpu_ids)


@dataclass
class QueuedJob:
    """Represents a job in the queue."""
    job_id: str
    output_dir: str
    script_path: str
    args: dict[str, Any]
    submitted_at: str
    status: str = "queued"  # queued, running, completed, failed, cancelled
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    gpu_id: Optional[str] = None
    error: Optional[str] = None
    pid: Optional[int] = None


class JobQueue:
    """FIFO job queue with GPU-aware scheduling.

    Features:
    - FIFO ordering of jobs
    - Configurable max concurrent jobs
    - Automatic GPU assignment from pool
    - Persistent queue state for recovery
    - Thread-safe operations
    """

    def __init__(
        self,
        max_workers: int = 1,
        gpu_ids: list[str] = None,
        jobs_dir: Path = None,
        state_file: Path = None
    ):
        """Initialize the job queue.

        Args:
            max_workers: Maximum concurrent jobs (default: 1)
            gpu_ids: List of GPU IDs. Auto-detects if None.
            jobs_dir: Directory to store job data
            state_file: Path to queue state file for persistence
        """
        self.max_workers = max_workers
        self.jobs_dir = jobs_dir or Path(__file__).parent.parent.parent / "jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = state_file or self.jobs_dir / "queue_state.json"

        # Initialize GPU pool
        self.gpu_pool = GPUPool(gpu_ids)

        # Adjust max_workers to not exceed GPU count
        if self.max_workers > self.gpu_pool.total_gpus():
            logger.warning(
                f"max_workers ({self.max_workers}) exceeds GPU count ({self.gpu_pool.total_gpus()}). "
                f"Limiting to {self.gpu_pool.total_gpus()}."
            )
            self.max_workers = self.gpu_pool.total_gpus()

        # Job tracking
        self._queue: deque[str] = deque()  # Queue of job_ids
        self._jobs: dict[str, QueuedJob] = {}  # job_id -> QueuedJob
        self._running: dict[str, subprocess.Popen] = {}  # job_id -> process
        self._lock = threading.Lock()

        # Worker thread
        self._running_flag = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

        # Load any persisted state
        self._load_state()

        logger.info(
            f"JobQueue initialized: max_workers={self.max_workers}, "
            f"gpus={self.gpu_pool.gpu_ids}"
        )

    def submit(
        self,
        script_path: str,
        args: dict[str, Any],
        output_dir: str,
        job_name: str = None
    ) -> dict[str, Any]:
        """Submit a job to the queue.

        Args:
            script_path: Path to the script to run
            args: Arguments to pass to the script
            output_dir: Directory for job output
            job_name: Optional name for the job

        Returns:
            Dict with job_id, status, and queue position
        """
        job_id = str(uuid.uuid4())[:8]

        # Create job directory
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        # Create job record
        job = QueuedJob(
            job_id=job_id,
            output_dir=output_dir,
            script_path=script_path,
            args=args,
            submitted_at=datetime.now().isoformat()
        )

        with self._lock:
            self._jobs[job_id] = job
            self._queue.append(job_id)
            position = len(self._queue)
            self._save_job_metadata(job)
            self._save_state()

        logger.info(f"Job {job_id} submitted to queue at position {position}")

        return {
            "status": "queued",
            "job_id": job_id,
            "position": position,
            "queue_length": len(self._queue),
            "message": f"Job queued at position {position}. Use get_job_status('{job_id}') to check progress."
        }

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Get status of a specific job.

        Args:
            job_id: ID of the job

        Returns:
            Dict with job status and details
        """
        with self._lock:
            if job_id not in self._jobs:
                # Try loading from disk
                job = self._load_job_metadata(job_id)
                if not job:
                    return {"status": "error", "error": f"Job {job_id} not found"}
                self._jobs[job_id] = job

            job = self._jobs[job_id]

            # Calculate queue position
            position = None
            if job.status == "queued":
                try:
                    position = list(self._queue).index(job_id) + 1
                except ValueError:
                    position = None
            elif job.status == "running":
                position = 0  # Running jobs are at position 0

            return {
                "status": "success",
                "job_id": job_id,
                "job_status": job.status,
                "queue_position": position,
                "output_dir": job.output_dir,
                "gpu_id": job.gpu_id,
                "submitted_at": job.submitted_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "error": job.error
            }

    def get_queue_status(self) -> dict[str, Any]:
        """Get overall queue status.

        Returns:
            Dict with queue length, running jobs, and GPU status
        """
        with self._lock:
            running_jobs = [
                {
                    "job_id": job_id,
                    "gpu_id": self._jobs[job_id].gpu_id,
                    "started_at": self._jobs[job_id].started_at
                }
                for job_id in self._running
                if job_id in self._jobs
            ]

            queued_jobs = [
                {
                    "job_id": job_id,
                    "position": i + 1,
                    "submitted_at": self._jobs[job_id].submitted_at
                }
                for i, job_id in enumerate(self._queue)
                if job_id in self._jobs
            ]

            return {
                "status": "success",
                "queue_length": len(self._queue),
                "running_count": len(self._running),
                "max_workers": self.max_workers,
                "running_jobs": running_jobs,
                "queued_jobs": queued_jobs[:10],  # Limit to first 10
                "available_gpus": self.gpu_pool.available_gpus(),
                "total_gpus": self.gpu_pool.total_gpus(),
                "gpu_assignments": self.gpu_pool.in_use_gpus()
            }

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        """Cancel a queued or running job.

        Args:
            job_id: ID of the job to cancel

        Returns:
            Dict with cancellation result
        """
        with self._lock:
            if job_id not in self._jobs:
                return {"status": "error", "error": f"Job {job_id} not found"}

            job = self._jobs[job_id]

            if job.status == "queued":
                # Remove from queue
                try:
                    self._queue.remove(job_id)
                except ValueError:
                    pass
                job.status = "cancelled"
                job.completed_at = datetime.now().isoformat()
                self._save_job_metadata(job)
                self._save_state()
                return {"status": "success", "message": f"Job {job_id} cancelled (was queued)"}

            elif job.status == "running":
                # Terminate process
                if job_id in self._running:
                    self._running[job_id].terminate()
                    # GPU will be released in _worker_loop when process ends
                job.status = "cancelled"
                job.completed_at = datetime.now().isoformat()
                self._save_job_metadata(job)
                return {"status": "success", "message": f"Job {job_id} cancelled (was running)"}

            else:
                return {"status": "error", "error": f"Job {job_id} is already {job.status}"}

    def get_position(self, job_id: str) -> Optional[int]:
        """Get position of a job in the queue.

        Returns:
            Position (1-indexed) if queued, 0 if running, None if not in queue
        """
        with self._lock:
            if job_id in self._running:
                return 0
            try:
                return list(self._queue).index(job_id) + 1
            except ValueError:
                return None

    def get_resource_status(self) -> dict[str, Any]:
        """Get current resource usage status.

        This helps verify that resources are properly freed when idle.

        Returns:
            Dict with resource usage information
        """
        import sys

        with self._lock:
            jobs_in_memory = len(self._jobs)
            queued_count = len(self._queue)
            running_count = len(self._running)
            gpus_in_use = self.gpu_pool.in_use_gpus()
            gpus_available = self.gpu_pool.available_gpus()

        # Check if truly idle (no jobs, all GPUs free)
        is_idle = (queued_count == 0 and running_count == 0)
        all_gpus_free = len(gpus_in_use) == 0

        return {
            "status": "success",
            "is_idle": is_idle,
            "all_gpus_free": all_gpus_free,
            "resource_usage": {
                "jobs_in_memory": jobs_in_memory,
                "queued_jobs": queued_count,
                "running_jobs": running_count,
                "gpus_in_use": gpus_in_use,
                "gpus_available": gpus_available,
                "total_gpus": self.gpu_pool.total_gpus(),
            },
            "message": (
                "All resources free. GPUs available for other programs."
                if (is_idle and all_gpus_free)
                else f"Active: {running_count} running, {queued_count} queued, {len(gpus_in_use)} GPUs in use"
            )
        }

    def _worker_loop(self) -> None:
        """Background worker that processes the queue.

        Uses adaptive sleep intervals to minimize CPU usage when idle:
        - 5 seconds when queue is empty and no jobs running
        - 2 seconds when jobs are running (to detect completion promptly)
        - 0.5 seconds when queue has pending jobs (to start them quickly)
        """
        logger.info("Queue worker started")
        cleanup_counter = 0

        while self._running_flag:
            try:
                # Check for completed jobs
                self._check_completed_jobs()

                # Try to start next job if resources available
                self._try_start_next_job()

                # Periodic cleanup of old completed jobs from memory
                cleanup_counter += 1
                if cleanup_counter >= 60:  # Every ~60 iterations
                    self._cleanup_old_jobs()
                    cleanup_counter = 0

                # Adaptive sleep based on queue state
                with self._lock:
                    has_queued = len(self._queue) > 0
                    has_running = len(self._running) > 0

                if has_queued:
                    # Jobs waiting - check frequently to start them
                    time.sleep(0.5)
                elif has_running:
                    # Jobs running - check periodically for completion
                    time.sleep(2)
                else:
                    # Idle - minimal polling
                    time.sleep(5)

            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                time.sleep(5)

    def _cleanup_old_jobs(self, max_age_hours: int = 24) -> None:
        """Remove completed/failed jobs from memory after max_age_hours.

        Jobs are still persisted on disk and can be loaded if needed.
        This prevents memory growth from accumulating job metadata.
        """
        now = datetime.now()
        to_remove = []

        with self._lock:
            for job_id, job in self._jobs.items():
                # Only clean up finished jobs
                if job.status not in ("completed", "failed", "cancelled"):
                    continue

                # Check age
                if job.completed_at:
                    try:
                        completed = datetime.fromisoformat(job.completed_at)
                        age_hours = (now - completed).total_seconds() / 3600
                        if age_hours > max_age_hours:
                            to_remove.append(job_id)
                    except (ValueError, TypeError):
                        pass

            for job_id in to_remove:
                self._jobs.pop(job_id, None)

        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} old jobs from memory")

    def _check_completed_jobs(self) -> None:
        """Check for completed jobs and release their resources."""
        with self._lock:
            completed = []
            for job_id, process in list(self._running.items()):
                if process.poll() is not None:  # Process has finished
                    completed.append((job_id, process.returncode))

            for job_id, returncode in completed:
                self._running.pop(job_id, None)
                if job_id in self._jobs:
                    job = self._jobs[job_id]
                    job.completed_at = datetime.now().isoformat()

                    if returncode == 0:
                        job.status = "completed"
                        logger.info(f"Job {job_id} completed successfully")
                    else:
                        job.status = "failed"
                        job.error = f"Process exited with code {returncode}"
                        logger.warning(f"Job {job_id} failed with code {returncode}")

                    # Release GPU - this is critical for freeing GPU memory
                    # The subprocess has terminated, so all GPU memory is already freed
                    # This just updates our tracking of which GPUs are available
                    if job.gpu_id:
                        self.gpu_pool.release(job.gpu_id)
                        logger.info(f"GPU {job.gpu_id} released and available for other programs")

                    self._save_job_metadata(job)
                    self._save_state()

    def _try_start_next_job(self) -> None:
        """Try to start the next job in queue if resources are available."""
        with self._lock:
            # Check if we can run more jobs
            if len(self._running) >= self.max_workers:
                return

            if not self._queue:
                return

            # Try to acquire a GPU
            job_id = self._queue[0]  # Peek at front

            if job_id not in self._jobs:
                # Job was removed, skip it
                self._queue.popleft()
                return

            gpu_id = self.gpu_pool.acquire(job_id)
            if gpu_id is None:
                # No GPU available
                return

            # Dequeue and start the job
            self._queue.popleft()
            job = self._jobs[job_id]

            try:
                self._start_job(job, gpu_id)
            except Exception as e:
                logger.error(f"Failed to start job {job_id}: {e}")
                job.status = "failed"
                job.error = str(e)
                job.completed_at = datetime.now().isoformat()
                self.gpu_pool.release(gpu_id)
                self._save_job_metadata(job)

            self._save_state()

    def _start_job(self, job: QueuedJob, gpu_id: str) -> None:
        """Start a job's execution."""
        job.status = "running"
        job.started_at = datetime.now().isoformat()
        job.gpu_id = gpu_id

        # Create output directory
        output_dir = Path(job.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build command
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        cmd = [
            "python",
            job.script_path,
        ]

        # Add arguments
        for key, value in job.args.items():
            if value is not None:
                if isinstance(value, bool):
                    if value:
                        cmd.append(f"--{key}")
                else:
                    cmd.extend([f"--{key}", str(value)])

        # Setup environment with GPU assignment
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = gpu_id
        env["PYTHONUNBUFFERED"] = "1"
        # Triton JIT cache needs a writable directory
        env.setdefault("TRITON_HOME", "/tmp")

        # Create log file
        log_file = output_dir / "boltzgen_run.log"

        logger.info(f"Starting job {job.job_id} on GPU {gpu_id}")
        logger.debug(f"Command: {' '.join(cmd)}")

        # Start process
        with open(log_file, 'w') as log_f:
            process = subprocess.Popen(
                cmd,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=str(scripts_dir),
                start_new_session=True
            )

        job.pid = process.pid
        self._running[job.job_id] = process
        self._save_job_metadata(job)

        # Also save job info to output directory for compatibility
        job_info = {
            "job_id": job.job_id,
            "config": job.args.get("config"),
            "output_dir": job.output_dir,
            "protocol": job.args.get("protocol"),
            "num_designs": job.args.get("num_designs"),
            "budget": job.args.get("budget"),
            "cuda_device": gpu_id,
            "submitted_at": job.submitted_at,
            "started_at": job.started_at,
            "pid": job.pid
        }
        with open(output_dir / "job_info.json", 'w') as f:
            json.dump(job_info, f, indent=2)

    def _save_job_metadata(self, job: QueuedJob) -> None:
        """Save job metadata to disk."""
        job_dir = self.jobs_dir / job.job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        meta_file = job_dir / "metadata.json"
        with open(meta_file, 'w') as f:
            json.dump(asdict(job), f, indent=2)

    def _load_job_metadata(self, job_id: str) -> Optional[QueuedJob]:
        """Load job metadata from disk."""
        meta_file = self.jobs_dir / job_id / "metadata.json"
        if meta_file.exists():
            with open(meta_file) as f:
                data = json.load(f)
                return QueuedJob(**data)
        return None

    def _save_state(self) -> None:
        """Save queue state to disk for recovery."""
        state = {
            "max_workers": self.max_workers,
            "gpu_ids": self.gpu_pool.gpu_ids,
            "pending_jobs": list(self._queue),
            "running_jobs": {
                job_id: self._jobs[job_id].gpu_id
                for job_id in self._running
                if job_id in self._jobs
            }
        }
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def _load_state(self) -> None:
        """Load queue state from disk."""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file) as f:
                state = json.load(f)

            # Restore pending jobs to queue
            for job_id in state.get("pending_jobs", []):
                job = self._load_job_metadata(job_id)
                if job and job.status == "queued":
                    self._jobs[job_id] = job
                    self._queue.append(job_id)
                    logger.info(f"Restored pending job {job_id} to queue")

            # Note: Running jobs from previous session are considered failed
            # since the processes are no longer running
            for job_id, gpu_id in state.get("running_jobs", {}).items():
                job = self._load_job_metadata(job_id)
                if job and job.status == "running":
                    job.status = "failed"
                    job.error = "Server restarted while job was running"
                    job.completed_at = datetime.now().isoformat()
                    self._save_job_metadata(job)
                    logger.warning(f"Marked job {job_id} as failed (server restart)")

        except Exception as e:
            logger.error(f"Error loading queue state: {e}")

    def shutdown(self) -> None:
        """Shutdown the queue worker."""
        self._running_flag = False
        self._worker_thread.join(timeout=5)
        logger.info("Queue worker shutdown")


# Global queue instance - initialized lazily
_job_queue: Optional[JobQueue] = None
_queue_lock = threading.Lock()


def get_job_queue(
    max_workers: int = None,
    gpu_ids: list[str] = None,
    reinitialize: bool = False
) -> JobQueue:
    """Get or create the global job queue instance.

    Args:
        max_workers: Max concurrent jobs. Uses env var BOLTZGEN_MAX_WORKERS or defaults to 1.
        gpu_ids: List of GPU IDs. Uses env var BOLTZGEN_GPU_IDS or auto-detects.
        reinitialize: If True, recreate the queue with new settings.

    Returns:
        The global JobQueue instance
    """
    global _job_queue

    with _queue_lock:
        if _job_queue is None or reinitialize:
            # Get config from environment if not provided
            if max_workers is None:
                max_workers = int(os.environ.get("BOLTZGEN_MAX_WORKERS", "1"))

            if gpu_ids is None:
                gpu_ids_env = os.environ.get("BOLTZGEN_GPU_IDS")
                if gpu_ids_env:
                    gpu_ids = [g.strip() for g in gpu_ids_env.split(",")]

            if _job_queue is not None:
                _job_queue.shutdown()

            _job_queue = JobQueue(max_workers=max_workers, gpu_ids=gpu_ids)

        return _job_queue
