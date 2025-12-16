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
   - Submit a BoltzGen job asynchronously (returns immediately)
   - Returns 'submitted' status with output directory for monitoring
   - Job runs in background independently

3. boltzgen_check_status
   - Check status and results of a submitted or running job
   - Returns statistics on generated designs

Available Protocols:
Users can choose from five different protocols optimized for specific use cases:
- protein-anything: General protein binder design (default)
- peptide-anything: Peptide binder design (filters cysteines, lower diversity)
- protein-small_molecule: Protein-small molecule interaction design (includes affinity metrics)
- nanobody-anything: Nanobody binder design (filters cysteines)
- antibody-anything: Antibody binder design (filters cysteines)

Workflow Overview:
1. Structure Generation: Generate protein structures using Boltz models
2. Sampling: Multiple sampling strategies for diverse designs
3. Quality Assessment: Evaluate and rank generated structures

Usage:
    # Run the MCP server
    python boltzgen_mcp.py

    # Or use with uvicorn for production
    uvicorn boltzgen_mcp:mcp --host 0.0.0.0 --port 8000
"""

from loguru import logger
from fastmcp import FastMCP

# Import tool MCPs
from tools.boltzgen_design import boltzgen_design_mcp

# Server definition and mounting
mcp = FastMCP(name="boltzgen")
logger.info("Mounting boltzgen_design tool")
mcp.mount(boltzgen_design_mcp)

if __name__ == "__main__":
    logger.info("Starting BoltzGen MCP server")
    mcp.run()
