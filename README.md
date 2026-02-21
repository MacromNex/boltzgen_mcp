# BoltzGen MCP

**AI-powered protein design via Docker and Model Context Protocol**

Design protein binders, peptide binders, and custom proteins using BoltzGen with:
- **Protein Binder Design** — Design proteins that bind to target proteins
- **Peptide Binder Design** — Generate peptides with optimized sequences
- **Multiple Protocols** — Support for antibodies, nanobodies, and small molecule interactions
- **Async Job Queue** — FIFO scheduling with GPU-aware resource management
- **Docker Deployment** — Pre-built images with all dependencies included

## Quick Start with Docker

### Approach 1: Pull Pre-built Image from GitHub

The fastest way to get started. A pre-built Docker image is automatically published to GitHub Container Registry on every release.

```bash
# Pull the latest image
docker pull ghcr.io/macromnex/boltzgen_mcp:latest

# Register with Claude Code (runs as current user to avoid permission issues)
claude mcp add boltzgen -- docker run -i --rm --user `id -u`:`id -g` --gpus all --ipc=host -v `pwd`:`pwd` ghcr.io/macromnex/boltzgen_mcp:latest
```

**Note:** Run from your project directory. `${pwd}` expands to the current working directory.

**Requirements:**
- Docker with GPU support (`nvidia-docker` or Docker with NVIDIA runtime)
- Claude Code installed

That's it! The BoltzGen MCP server is now available in Claude Code.

---

### Approach 2: Build Docker Image Locally

Build the image yourself and install it into Claude Code. Useful for customization or offline environments.

```bash
# Clone the repository
git clone https://github.com/MacromNex/boltzgen_mcp.git
cd boltzgen_mcp

# Build the Docker image
docker build -t boltzgen_mcp:latest .

# Register with Claude Code (runs as current user to avoid permission issues)
claude mcp add boltzgen -- docker run -i --rm --user `id -u`:`id -g` --gpus all --ipc=host -v `pwd`:`pwd` boltzgen_mcp:latest
```

**Note:** Run from your project directory. `${pwd}` expands to the current working directory.

**Requirements:**
- Docker with GPU support
- Claude Code installed
- Git (to clone the repository)

**About the Docker Flags:**
- `-i` — Interactive mode for Claude Code
- `--rm` — Automatically remove container after exit
- `--user ${id -u}:${id -g}` — Runs the container as your current user, so output files are owned by you (not root)
- `--gpus all` — Grants access to all available GPUs
- `--ipc=host` — Uses host IPC namespace for better performance
- `-v` — Mounts your project directory so the container can access your data

---

## Verify Installation

After adding the MCP server, you can verify it's working:

```bash
# List registered MCP servers
claude mcp list

# You should see 'boltzgen' in the output
```

In Claude Code, you can now use all 8 BoltzGen tools:
- `boltzgen_run` — Synchronous protein design
- `boltzgen_submit` — Submit async design jobs
- `boltzgen_check_status` — Monitor job progress by output directory
- `boltzgen_job_status` — Check job by ID
- `boltzgen_queue_status` — View queue and GPU availability
- `boltzgen_cancel_job` — Cancel jobs
- `boltzgen_configure_queue` — Set max workers and GPU configuration
- `boltzgen_resource_status` — Verify GPU resource management

---

## Next Steps

- **Detailed documentation**: See [details.md](details.md) for comprehensive guides on:
  - Local Python environment setup (alternative to Docker)
  - Available MCP tools and parameters
  - Example workflows and tutorials
  - Configuration file formats
  - Troubleshooting

---

## Usage Examples

Once registered, you can use the BoltzGen tools directly in Claude Code. Here are some common workflows:

### Example 1: Quick Protein Design

```
Submit protein binder design for @examples/data/1g13prot.yaml
with output_dir "results/1g13_design" and num_designs 5
```

### Example 2: Peptide Binder with Quality Focus

```
Submit peptide binder design for @examples/data/beetletert.yaml
with output_dir "results/peptide_design", alpha 0.01 (quality focused),
and num_designs 10
```

### Example 3: Async Job Submission and Monitoring

```
1. Submit async protein design for @examples/data/1g13prot.yaml
   with output_dir "results/async_design" and num_designs 10
2. Check job status every 30 seconds
3. When complete, show me the generated structures
```

### Example 4: Batch Processing Multiple Targets

```
Submit batch protein design for these configs:
- @examples/data/1g13prot.yaml (1G13 protein)
- @examples/data/beetletert.yaml (BeetleTert)
- @examples/data/pdl1_simplified.yaml (PDL1)

Save to output_base_dir "results/batch" with num_designs 5 each
```

### Example 5: Validate Configuration Before Design

```
Validate these configs and show me any issues:
- @examples/data/1g13prot.yaml
- @examples/data/beetletert.yaml
- @examples/data/chorismite.yaml
```

### Example 6: Monitor Job Queue

```
Show me the current job queue status and available GPUs
```

---

## Demo Data

Example configuration files are included in `examples/data/`:

| File | Description | Use Case |
|------|-------------|----------|
| `1g13prot.yaml` | 1G13 protein binder design | Protein-protein interactions |
| `beetletert.yaml` | BeetleTert peptide design | Peptide drug discovery |
| `pdl1_simplified.yaml` | PDL1 antibody design | Antibody engineering |
| `chorismite.yaml` | Small molecule binding | Enzyme design |
| `penguinpox.yaml` | Nanobody design | Nanobody development |

---

## Supported Protocols

All tools support the following design protocols:
- `protein-anything` (default) — General protein binder design
- `peptide-anything` — Peptide design with cysteine filtering
- `protein-small_molecule` — Small molecule interactions
- `nanobody-anything` — Nanobody CDR design
- `antibody-anything` — Antibody design

## GPU Support

Docker setup fully supports:
- Multi-GPU systems (specify device via `cuda:0`, `cuda:1`, etc.)
- Single GPU setup
- CPU-only inference (slower, use `cpu` device)

---

## Troubleshooting

**Docker not found?**
```bash
docker --version  # Install Docker if missing
```

**GPU not accessible?**
- Ensure NVIDIA Docker runtime is installed
- Check with `docker run --gpus all ubuntu nvidia-smi`

**Claude Code not found?**
```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code
```

**Permission issues with output files?**
The Docker setup automatically runs as your current user. If you still see permission issues:
```bash
# Rebuild with your user ID
docker build --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g) -t boltzgen_mcp:latest .
```

---

## Local Setup (Alternative to Docker)

For development or custom environments, see [details.md](details.md#installation) for:
- Manual conda environment setup
- Direct Python script execution
- Custom configuration options

---

## License

Based on the original [BoltzGen](https://github.com/HannesStark/boltzgen) repository by Hannes Stark et al.
MCP integration built using [FastMCP](https://github.com/jlowin/fastmcp) framework.
