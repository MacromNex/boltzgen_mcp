# BoltzGen MCP

> AI-powered protein design through the Model Context Protocol - Design protein binders, peptide binders, and custom proteins with BoltzGen

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [Local Usage (Scripts)](#local-usage-scripts)
- [MCP Server Installation](#mcp-server-installation)
- [Using with Claude Code](#using-with-claude-code)
- [Using with Gemini CLI](#using-with-gemini-cli)
- [Available Tools](#available-tools)
- [Examples](#examples)
- [Demo Data](#demo-data)
- [Configuration Files](#configuration-files)
- [Troubleshooting](#troubleshooting)

## Overview

BoltzGen MCP provides AI assistants (Claude Code, Gemini) with access to BoltzGen, a state-of-the-art protein design platform. This MCP server enables seamless protein design workflows including protein binders, peptide binders, nanobodies, and antibodies through simple conversational prompts.

### Features
- **Protein Binder Design**: Design proteins that bind to target proteins using protein-anything protocol
- **Peptide Binder Design**: Generate peptides (including cyclic) with cysteine filtering optimization
- **Flexible Protocols**: Support for protein-small_molecule, nanobody-anything, and antibody-anything
- **Asynchronous Job Management**: Submit long-running jobs and track progress with real-time logs
- **Batch Processing**: Process multiple targets efficiently in parallel
- **Quick Validation**: Fast configuration file validation without full pipeline execution

### Directory Structure
```
./
├── README.md               # This file
├── env/                    # Conda environment with BoltzGen and dependencies
├── src/
│   └── server.py           # MCP server with 10 tools
├── scripts/
│   ├── protein_binder_design.py    # Protein binder design using protein-anything
│   ├── peptide_binder_design.py    # Peptide binder design with cysteine filtering
│   ├── run_boltzgen.py             # Generic BoltzGen runner for any protocol
│   ├── check_config.py             # Fast configuration validation
│   └── lib/                        # Shared utilities and job management
├── examples/
│   └── data/               # Demo configurations and structures
├── configs/                # Default configuration templates
├── jobs/                   # Active and completed job tracking
└── reports/                # Documentation and analysis reports
```

---

## Installation

### Prerequisites
- Conda or Mamba (mamba recommended for faster installation)
- Python 3.10+
- 8+ GB RAM, 7+ GB GPU memory recommended for protein design

### Create Environment
Following the verified procedure from `reports/step3_environment.md`:

```bash
# Navigate to the MCP directory
cd /home/xux/Desktop/ProteinMCP/ProteinMCP/tool-mcps/boltzgen_mcp

# Create conda environment (use mamba if available)
mamba create -p ./env python=3.12 -y
# or: conda create -p ./env python=3.12 -y

# Activate environment
mamba activate ./env
# or: conda activate ./env

# Install core dependencies
pip install fastmcp==2.13.3 loguru==0.7.3

# Install BoltzGen (this installs PyTorch, protein libraries, etc.)
pip install boltzgen

# Verify installation
python -c "from src.server import mcp; print('BoltzGen MCP server ready!')"
```

---

## Local Usage (Scripts)

You can use the scripts directly without MCP for local processing.

### Available Scripts

| Script | Description | Example Use Case |
|--------|-------------|------------------|
| `scripts/protein_binder_design.py` | Design protein binders using protein-anything protocol | Target protein binding |
| `scripts/peptide_binder_design.py` | Design peptide binders with cysteine filtering | Peptide drug discovery |
| `scripts/run_boltzgen.py` | Run any BoltzGen protocol with custom parameters | Custom protocols |
| `scripts/check_config.py` | Fast validation of BoltzGen configurations | Pre-flight checks |

### Script Examples

#### Protein Binder Design

```bash
# Activate environment
mamba activate ./env

# Design protein binders for target protein
python scripts/protein_binder_design.py \
  --input examples/data/1g13prot.yaml \
  --output results/protein_binder_1g13 \
  --num_designs 10 \
  --budget 2
```

**Parameters:**
- `--input, -i`: BoltzGen YAML configuration file (required)
- `--output, -o`: Output directory for designed proteins (required)
- `--num_designs`: Number of designs to generate (default: 10)
- `--budget`: Computational budget for design quality (default: 2)
- `--cuda_device`: CUDA device ID (auto-detected if None)

#### Peptide Binder Design

```bash
python scripts/peptide_binder_design.py \
  --input examples/data/beetletert.yaml \
  --output results/peptide_binder \
  --alpha 0.01 \
  --num_designs 15
```

**Parameters:**
- `--alpha`: Diversity vs quality trade-off (0.0=quality focused, 1.0=diversity focused)
- Other parameters same as protein binder design

#### Configuration Validation

```bash
# Quick validation before full design run
python scripts/check_config.py \
  --config examples/data/1g13prot.yaml \
  --verbose
```

---

## MCP Server Installation

### Option 1: Using fastmcp (Recommended)

```bash
# Install MCP server for Claude Code
fastmcp install src/server.py --name boltzgen
```

### Option 2: Manual Installation for Claude Code

```bash
# Add MCP server to Claude Code
claude mcp add boltzgen -- $(pwd)/env/bin/python $(pwd)/src/server.py

# Verify installation
claude mcp list
# Should show: boltzgen: ... - ✓ Connected
```

### Option 3: Configure in settings.json

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "boltzgen": {
      "command": "/home/xux/Desktop/ProteinMCP/ProteinMCP/tool-mcps/boltzgen_mcp/env/bin/python",
      "args": ["/home/xux/Desktop/ProteinMCP/ProteinMCP/tool-mcps/boltzgen_mcp/src/server.py"]
    }
  }
}
```

---

## Using with Claude Code

After installing the MCP server, you can use it directly in Claude Code.

### Quick Start

```bash
# Start Claude Code
claude
```

### Example Prompts

#### Tool Discovery
```
What tools are available from boltzgen?
```

#### Configuration Validation
```
Use validate_config with config_file "@examples/data/1g13prot.yaml"
```

#### Basic Protein Design
```
Submit protein binder design for @examples/data/1g13prot.yaml
with output_dir "results/test_design" and num_designs 5
```

#### Peptide Design with Parameters
```
Submit peptide binder design for @examples/data/beetletert.yaml
with alpha 0.01 (quality focused) and budget 2
```

#### Job Monitoring
```
Submit a protein design job, then:
1. Check its status every 30 seconds
2. Show me the last 20 lines of the log
3. Get the results when it completes
```

#### Batch Processing
```
Submit batch protein design for these configs:
- @examples/data/1g13prot.yaml
- @examples/data/beetletert.yaml
- @examples/data/pdl1_simplified.yaml

Save to output_base_dir "results/batch_design"
```

### Using @ References

In Claude Code, use `@` to reference files and directories:

| Reference | Description |
|-----------|-------------|
| `@examples/data/1g13prot.yaml` | Reference a specific config file |
| `@examples/data/` | Reference the data directory |
| `@configs/default_config.json` | Reference default config template |
| `@results/` | Reference output directory |

---

## Using with Gemini CLI

### Configuration

Add to `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "boltzgen": {
      "command": "/home/xux/Desktop/ProteinMCP/ProteinMCP/tool-mcps/boltzgen_mcp/env/bin/python",
      "args": ["/home/xux/Desktop/ProteinMCP/ProteinMCP/tool-mcps/boltzgen_mcp/src/server.py"]
    }
  }
}
```

### Example Prompts

```bash
# Start Gemini CLI
gemini

# Example prompts (same as Claude Code)
> What tools are available?
> Submit protein binder design for examples/data/1g13prot.yaml
> Check job status and show logs
```

---

## Available Tools

### Quick Operations (Sync API)

These tools return results immediately (< 30 seconds):

| Tool | Description | Parameters | Example |
|------|-------------|------------|---------|
| `validate_config` | Validate BoltzGen configuration file | `config_file`, `verbose` | Quick pre-flight check |

### Long-Running Tasks (Submit API)

These tools return a job_id for tracking (5-30 minutes):

| Tool | Description | Est. Runtime | Parameters |
|------|-------------|--------------|------------|
| `submit_protein_binder_design` | Design protein binders | 5-20 min | `config_file`, `output_dir`, `num_designs`, `budget` |
| `submit_peptide_binder_design` | Design peptide binders | 5-15 min | `config_file`, `output_dir`, `alpha`, `num_designs` |
| `submit_generic_boltzgen` | Run any BoltzGen protocol | 5-30 min | `config_file`, `protocol`, `output_dir` |
| `submit_batch_protein_design` | Batch process multiple targets | Variable | `config_files`, `output_base_dir` |

### Job Management Tools

| Tool | Description |
|------|-------------|
| `get_job_status` | Check job progress (pending → running → completed/failed) |
| `get_job_result` | Get results when completed |
| `get_job_log` | View execution logs (supports tail parameter) |
| `cancel_job` | Cancel running job |
| `list_jobs` | List all jobs with optional status filtering |

---

## Examples

### Example 1: Protein Binder Design for 1G13

**Goal:** Design protein binders that bind to the 1G13 protein structure

**Using Script:**
```bash
python scripts/protein_binder_design.py \
  --input examples/data/1g13prot.yaml \
  --output results/1g13_binders \
  --num_designs 10
```

**Using MCP (in Claude Code):**
```
Submit protein binder design for @examples/data/1g13prot.yaml
with output_dir "results/1g13_binders" and num_designs 10
```

**Expected Output:**
- 10 designed protein structures in CIF/PDB format
- Design logs showing generation and filtering steps
- Statistics on design quality and diversity

### Example 2: Peptide Binder Design for BeetleTert

**Goal:** Design quality-focused peptides that bind to BeetleTert protein

**Using Script:**
```bash
python scripts/peptide_binder_design.py \
  --input examples/data/beetletert.yaml \
  --output results/beetletert_peptides \
  --alpha 0.01 \
  --num_designs 20
```

**Using MCP (in Claude Code):**
```
Submit peptide binder design for @examples/data/beetletert.yaml
with output_dir "results/beetletert_peptides", alpha 0.01, and num_designs 20
```

**Expected Output:**
- 20 designed peptide structures with cysteine filtering
- Diversity analysis and binding predictions
- Quality-focused designs due to low alpha value

### Example 3: Configuration Validation Workflow

**Goal:** Validate multiple configurations before submitting long jobs

**Using Script:**
```bash
for config in examples/data/*.yaml; do
  echo "Validating $config..."
  python scripts/check_config.py --config "$config" --verbose
done
```

**Using MCP (in Claude Code):**
```
Validate all YAML configs in @examples/data/ and show me which ones are valid:
- Check @examples/data/1g13prot.yaml
- Check @examples/data/beetletert.yaml
- Check @examples/data/pdl1_simplified.yaml
```

### Example 4: Batch Processing Multiple Targets

**Goal:** Process multiple protein targets efficiently

**Using MCP (in Claude Code):**
```
Submit batch protein design for these three targets:
- @examples/data/1g13prot.yaml (1G13 protein)
- @examples/data/beetletert.yaml (BeetleTert)
- @examples/data/pdl1_simplified.yaml (PDL1)

Save to output_base_dir "results/multi_target_batch" with num_designs 5 each
```

**Expected Output:**
- Three subdirectories: `1g13prot_protein_design/`, `beetletert_protein_design/`, `pdl1_simplified_protein_design/`
- 5 designs per target (15 total designs)
- Batch processing logs showing progress through all targets

---

## Demo Data

The `examples/data/` directory contains sample configurations for testing:

| File | Description | Target Structure | Use With |
|------|-------------|------------------|----------|
| `1g13prot.yaml` | Protein binder design for 1G13 | `1g13.cif` | protein_binder_design |
| `beetletert.yaml` | Peptide binder with binding site | `5cqg.cif` | peptide_binder_design |
| `chorismite.yaml` | Small molecule binding design | TSA ligand | generic_boltzgen |
| `penguinpox.yaml` | Nanobody CDR design | `9bkq-assembly2.cif` | generic_boltzgen |
| `pdl1_simplified.yaml` | Simplified antibody design | `7rpz.cif` | protein_binder_design |
| `pdl1.yaml` | Full antibody design config | `7rpz.cif` | protein_binder_design |

### Additional Structure Files
- `8r3a.cif` - Additional protein structure for testing
- `pdl1_simplified.cif` - Standalone structure file

---

## Configuration Files

The `configs/` directory contains configuration templates:

| Config | Description | Parameters |
|--------|-------------|------------|
| `default_config.json` | Default settings for all tools | `protocol`, `num_designs`, `budget`, `distributed` |
| `protein_binder_config.json` | Optimized for protein binder design | `protein-anything` protocol settings |
| `peptide_binder_config.json` | Optimized for peptide design | `peptide-anything` with cysteine filtering |

### Config Example

```json
{
  "protocol": "protein-anything",
  "num_designs": 10,
  "budget": 2,
  "distributed": {
    "master_port": 29500
  },
  "compute": {
    "cuda_device": null
  },
  "output": {
    "format": ["cif", "pdb"],
    "include_metadata": true
  }
}
```

---

## Troubleshooting

### Environment Issues

**Problem:** Environment not found
```bash
# Recreate environment
mamba create -p ./env python=3.12 -y
mamba activate ./env
pip install fastmcp loguru boltzgen
```

**Problem:** BoltzGen command not found
```bash
# Verify BoltzGen installation
mamba run -p ./env boltzgen --help

# If missing, reinstall
pip install --force-reinstall boltzgen
```

**Problem:** Import errors
```bash
# Verify core imports
python -c "
import fastmcp, loguru
from src.server import mcp
print('All imports working')
"
```

### MCP Issues

**Problem:** Server not found in Claude Code
```bash
# Check MCP registration
claude mcp list

# Re-add if needed
claude mcp remove boltzgen
claude mcp add boltzgen -- $(pwd)/env/bin/python $(pwd)/src/server.py
```

**Problem:** Tools not working
```bash
# Test server directly
python -c "
from src.server import mcp
tools = list(mcp.list_tools().keys())
print(f'Available tools: {tools}')
"
```

**Problem:** FastMCP issues
```bash
# Test FastMCP server manually
mamba run -p ./env python src/server.py
# Should start without errors and show "Server ready"
```

### Job Issues

**Problem:** Job stuck in pending
```bash
# Check job directory
ls -la jobs/

# Check job logs
ls jobs/*/job.log
```

**Problem:** Job failed with error
```
# In Claude Code:
Use get_job_log with job_id "<job_id>" and tail 100 to see error details
```

**Problem:** CUDA errors
```bash
# Check GPU availability
nvidia-smi

# Use CPU if needed
python scripts/protein_binder_design.py --input config.yaml --output results/ --cuda_device cpu
```

**Problem:** Port conflicts
```bash
# Check if port is in use
netstat -tulpn | grep 29500

# Use different port
python scripts/protein_binder_design.py --master_port 29501
```

### Configuration Issues

**Problem:** "Configuration file not found"
```bash
# Check file exists
ls -la examples/data/1g13prot.yaml

# Use absolute path
realpath examples/data/1g13prot.yaml
```

**Problem:** "Missing structure file"
```
# This is often shown in job logs. Check the config file references correct .cif files
Use validate_config to see specific missing files
```

**Problem:** YAML parsing errors
```bash
# Validate YAML syntax
python -c "
import yaml
with open('examples/data/1g13prot.yaml') as f:
    data = yaml.safe_load(f)
print('YAML valid')
"
```

---

## Development

### Running Tests

```bash
# Activate environment
mamba activate ./env

# Test server startup
python -c "from src.server import mcp; print('Server OK')"

# Test job system
python -c "
import sys; sys.path.insert(0, 'src')
from jobs.manager import job_manager
result = job_manager.list_jobs()
print(f'Job system: {result[\"status\"]}')
"
```

### Starting Dev Server

```bash
# Run MCP server in development mode
fastmcp dev src/server.py

# Or run directly
mamba run -p ./env python src/server.py
```

---

## Performance Notes

### Resource Requirements
- **Memory**: 8-16 GB RAM for typical designs
- **GPU**: 7+ GB VRAM recommended (BoltzGen can use CPU but much slower)
- **Disk**: 1-5 GB per design for temporary and output files
- **Network**: Ports 29500-29600 for distributed training

### Optimization Tips
- **Use lower budget**: Set `budget=1` for faster (lower quality) designs
- **Specify GPU**: Use `cuda_device="0"` to avoid device selection overhead
- **Batch processing**: More efficient than individual jobs for multiple targets
- **Monitor with logs**: Use `get_job_log` to track progress and identify bottlenecks

---

## License

This MCP server wraps BoltzGen, which has its own license terms. Please refer to the BoltzGen documentation for licensing information.

## Credits

Based on [BoltzGen](https://github.com/deepmind/boltzgen) by DeepMind for AI-powered protein design.
MCP integration built using [FastMCP](https://github.com/jlowin/fastmcp) framework.