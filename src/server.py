"""
Model Context Protocol (MCP) for BoltzGen

This MCP server provides protein design tools using BoltzGen.
It enables researchers to generate protein structures using Boltz models
for structure prediction and optimization.

This MCP Server contains tools for:

1. boltzgen_run
   - Run complete BoltzGen protein design pipeline (synchronous)
   - Uses Boltz models for structure generation
   - Supports multiple protocols and sampling strategies
   - Waits for completion and returns full results

2. boltzgen_submit
   - Submit a BoltzGen job to the queue (FIFO with GPU scheduling)
   - Jobs are processed in order with automatic GPU assignment
   - Multiple jobs can run in parallel if multiple GPUs configured

3. boltzgen_check_status
   - Check status and results of a submitted or running job
   - Returns statistics on generated designs

4. boltzgen_queue_status
   - View queue length, running jobs, and GPU availability
   - Monitor overall system status

5. boltzgen_cancel_job
   - Cancel a queued or running job

6. boltzgen_configure_queue
   - Configure max concurrent jobs and GPU settings
   - Supports multi-GPU parallel execution

7. boltzgen_job_status
   - Get status of a specific job by job_id

8. boltzgen_resource_status
   - Verify GPUs are freed when idle
   - Check that MCP server is not holding resources

Available Protocols:
Users can choose from five different protocols optimized for specific use cases:
- protein-anything: General protein binder design (default)
- peptide-anything: Peptide binder design (filters cysteines, lower diversity)
- protein-small_molecule: Protein-small molecule interaction design (includes affinity metrics)
- nanobody-anything: Nanobody binder design (filters cysteines)
- antibody-anything: Antibody binder design (filters cysteines)

Job Queue Configuration:
The server uses a FIFO job queue with GPU-aware scheduling:
- Default: 1 concurrent job (sequential execution)
- Configure via boltzgen_configure_queue or environment variables:
  - BOLTZGEN_MAX_WORKERS: Max concurrent jobs (default: 1)
  - BOLTZGEN_GPU_IDS: Comma-separated GPU IDs (e.g., "0,1")

Example for 2-GPU parallel execution:
    boltzgen_configure_queue(max_workers=2, gpu_ids="0,1")

Workflow Overview:
1. Structure Generation: Generate protein structures using Boltz models
2. Sampling: Multiple sampling strategies for diverse designs
3. Quality Assessment: Evaluate and rank generated structures

Usage:
    # Run the MCP server
    python server.py

    # Or use with uvicorn for production
    uvicorn server:mcp --host 0.0.0.0 --port 8000

    # With multi-GPU configuration (environment variables)
    BOLTZGEN_MAX_WORKERS=2 BOLTZGEN_GPU_IDS="0,1" python server.py
"""

import os
from loguru import logger
from fastmcp import FastMCP

# Import tool MCPs
from tools.boltzgen_design import boltzgen_design_mcp

# Initialize queue on import (ensures queue worker starts)
from jobs import get_job_queue

# Server definition and mounting
mcp = FastMCP(name="boltzgen")
logger.info("Mounting boltzgen_design tool")
mcp.mount(boltzgen_design_mcp)

if __name__ == "__main__":
    # Initialize job queue with environment configuration
    max_workers = int(os.environ.get("BOLTZGEN_MAX_WORKERS", "1"))
    gpu_ids_env = os.environ.get("BOLTZGEN_GPU_IDS")
    gpu_ids = [g.strip() for g in gpu_ids_env.split(",")] if gpu_ids_env else None

    queue = get_job_queue(max_workers=max_workers, gpu_ids=gpu_ids)

    logger.info("Starting BoltzGen MCP server")
    logger.info(f"Job queue: max_workers={queue.max_workers}, gpus={queue.gpu_pool.gpu_ids}")
    mcp.run()
