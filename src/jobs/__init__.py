"""Job management for BoltzGen MCP server.

Provides two execution modes:
1. Direct execution (job_manager) - immediate execution in threads
2. Queue-based execution (queue functions) - FIFO queue with GPU scheduling

For GPU-intensive tasks, use the queue-based functions:
- queue_job(): Submit a job to the FIFO queue
- get_queue_status(): Check queue length and running jobs
- get_queued_job_status(): Check status of a specific queued job
- cancel_queued_job(): Cancel a queued or running job
- configure_queue(): Change max_workers and GPU settings
"""

from .manager import (
    job_manager,
    JobStatus,
    queue_job,
    get_queue_status,
    get_queued_job_status,
    cancel_queued_job,
    configure_queue,
    get_resource_status,
)
from .queue import get_job_queue, JobQueue, GPUPool

__all__ = [
    # Original job manager
    "job_manager",
    "JobStatus",
    # Queue-based execution (recommended for GPU tasks)
    "queue_job",
    "get_queue_status",
    "get_queued_job_status",
    "cancel_queued_job",
    "configure_queue",
    "get_resource_status",
    # Queue classes for advanced usage
    "get_job_queue",
    "JobQueue",
    "GPUPool",
]