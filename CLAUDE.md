# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

BoltzGen MCP is a Model Context Protocol server wrapping [BoltzGen](https://github.com/HannesStark/boltzgen) for AI-powered protein structure design. It exposes 8 tools for synchronous/asynchronous protein design with GPU-aware job scheduling.

## Setup

```bash
bash quick_setup.sh                    # full setup (conda + deps + optional models)
bash quick_setup.sh --skip-repo        # skip cloning original boltzgen repo
USE_PACKED_ENVS=1 bash quick_setup.sh  # use pre-packaged conda env from GitHub Releases
```

Dependencies: `fastmcp==2.13.3`, `loguru==0.7.3`, `boltzgen` (Python 3.12).

## Running

```bash
# Start MCP server
env/bin/python src/server.py

# Run design directly (no MCP)
env/bin/python scripts/run_boltzgen.py --config examples/data/1g13prot.yaml --output results/test --protocol protein-anything

# Register with Claude Code
claude mcp add boltzgen -- ./env/bin/python src/server.py
```

Environment variables: `BOLTZGEN_MAX_WORKERS` (default 1), `BOLTZGEN_GPU_IDS` (comma-separated).

## Testing

```bash
env/bin/python -m pytest tests/test_import.py      # import and path checks
env/bin/python -m pytest tests/test_server.py       # server and tool registration
env/bin/python -m pytest tests/test_mcp_tools.py    # MCP protocol-level tests
env/bin/python tests/run_integration_tests.py       # full integration suite
```

## Docker

```bash
docker build -t boltzgen_mcp .
docker run --gpus all boltzgen_mcp
```

CI workflows in `.github/workflows/`: `docker.yml` builds/pushes to GHCR, `build-env.yml` packs and releases conda environments.

## Architecture

```
MCP Client → FastMCP Server (src/server.py)
                ↓ mounts
             Tools Layer (src/tools/boltzgen_design.py)
                ↓ delegates to
             Job Queue (src/jobs/queue.py) ← GPU Pool
                ↓ spawns
             Subprocess (scripts/run_boltzgen.py → boltzgen CLI)
```

**src/server.py** — FastMCP entry point. Creates the `"boltzgen"` server, mounts the tools sub-app, initializes the job queue singleton from env vars.

**src/tools/boltzgen_design.py** — Defines all 8 MCP tools. Sync tool (`boltzgen_run`) blocks and streams subprocess output. Async tools (`boltzgen_submit`, `boltzgen_job_status`, etc.) use the job queue. Each tool validates configs, resolves paths, builds `boltzgen` CLI commands, and parses output directories for results.

**src/jobs/queue.py** — `JobQueue` (singleton via `get_job_queue()`) with FIFO scheduling and `GPUPool` for thread-safe GPU allocation. A background worker thread monitors job completion, starts queued jobs when GPUs free up, and uses adaptive polling (5s idle → 0.5s when jobs queued). State persists to `jobs/queue_state.json`. Old jobs cleaned from memory after 24 hours.

**src/jobs/manager.py** — `JobManager` (legacy direct-execution mode) and wrapper functions (`queue_job`, `get_queue_status`, etc.) that delegate to the queue singleton. `JobStatus` enum lives here.

**scripts/run_boltzgen.py** — Standalone runner that sets up torch.distributed env vars (MASTER_ADDR, GLOO_SOCKET_IFNAME, etc.), validates YAML configs, and streams subprocess output with loguru logging. This is what the job queue spawns.

**configs/** — JSON defaults for protocol settings. `default_config.json` has distributed/compute/output/logging sections. Protocol-specific overrides in `protein_binder_config.json` and `peptide_binder_config.json`.

## Supported Protocols

- `protein-anything` — General protein binder design (default)
- `peptide-anything` — Peptide binder with cysteine filtering
- `protein-small_molecule` — Small molecule interactions
- `nanobody-anything` — Nanobody CDR design
- `antibody-anything` — Antibody design

## Key Patterns

- Config files are YAML (`.yaml`) pointing to structure files (`.cif`). Paths in YAML are resolved relative to the YAML file's directory.
- The job queue is a module-level singleton (`_job_queue` in `queue.py`). Access via `get_job_queue()`, reconfigure via `configure_queue()`.
- GPU detection uses `nvidia-smi --query-gpu=index --format=csv,noheader`. Falls back gracefully if no GPUs found.
- Model weights (~6GB) auto-download to `~/.cache` on first use.
