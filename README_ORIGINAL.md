# BoltzGen MCP service

## Overview
This repository creates MCP service for [BoltzGen](https://github.com/google-deepmind/boltzgen). It supports the BoltzGen binder design workflow:
1. Run BoltzGen with predefined a3m files

## Available Protocols
BoltzGen supports five different protocols optimized for specific use cases:

- **protein-anything** (default): General protein binder design
- **peptide-anything**: Peptide binder design (filters cysteines, uses lower diversity parameter)
- **protein-small_molecule**: Protein-small molecule interaction design (includes affinity metrics)
- **nanobody-anything**: Nanobody binder design (filters cysteines)
- **antibody-anything**: Antibody binder design (filters cysteines)

Each protocol applies specific configuration overrides optimized for the target application.

## Installation
```shell
mamba env create -p ./env python=3.12 pip -y 
mamba activate ./env
pip install --ignore-installed fastmcp loguru
pip install boltzgen
```

## Local usage
### 1. Design a protein binder against a protein target (most common)

```bash
boltzgen run example/vanilla_protein/1g13prot.yaml \
  --output results/protein_binder_1g13prot \
  --protocol protein-anything \
  --num_designs 100 \
  --budget 30
```
This is the default protocol for designing proteins that bind to protein targets.

### 2. Design a peptide binder against a protein target

```bash
boltzgen run example/vanilla_peptide_with_target_binding_site/beetletert.yaml \
  --output results/peptide_binder_beetletert \
  --protocol peptide-anything \
  --num_designs 100 \
  --budget 30 \
  --alpha 0.01
```
Use this for designing peptides (including cyclic peptides). Note: cysteines are avoided by default in inverse folding for this protocol.

### 3. **Design a protein to bind a small molecule**

```bash
boltzgen run example/protein_binding_small_molecule/chorismite.yaml \
  --output results/small_molecule_binder_chorismite \
  --protocol protein-small_molecule \
  --num_designs 100 \
  --budget 30
```
This includes binding affinity prediction for the protein-small molecule interaction.

### 4. **Design antibody CDRs**

```bash
boltzgen run example/fab_targets/pdl1.yaml \
  --output results/antibody_design_pdl1 \
  --protocol antibody-anything \
  --num_designs 100 \
  --budget 30
```

### 5. **Design nanobody CDRs**

```bash
boltzgen run example/nanobody/penguinpox.yaml \
  --output results/nanobody_design_penguinpox \
  --protocol nanobody-anything \
  --num_designs 100 \
  --budget 30
```
### Key Parameters Explanation:

- `--num_designs`: Number of intermediate designs (typically 10,000-60,000 for production)
- `--budget`: Number of final diverse designs after filtering (typically 30)
- `--protocol`: Determines default settings and which steps run
- `--alpha`: Diversity vs quality tradeoff (0.0=quality only, 1.0=diversity only)

### With script
```shell
python scripts/run_boltzgen.py --config example/nanobody/penguinpox.yaml --output results/nanobody_penguinpox --protocol  nanobody-anything \
--num_designs 10 --budget 2 --cuda_device 0
```

## MCP usage
### Debug MCP server
```shell
cd tool-mcps/boltzgen_mcp
mamba activate ./env
fastmcp run src/boltzgen_mcp.py:mcp --transport http --port 8001 --python ./env/bin/python 
# Test config path: /home/xux/Desktop/ProteinMCP/ProteinMCP/tool-mcps/boltzgen_mcp/example/nanobody/penguinpox.yaml
# Test output dir: /home/xux/Desktop/ProteinMCP/ProteinMCP/tool-mcps/boltzgen_mcp/results/nanobody_penguinpox_mcp
```

### Install MCP server
```shell
fastmcp install claude-code tool-mcps/boltzgen_mcp/src/boltzgen_mcp.py --python tool-mcps/boltzgen_mcp/env/bin/python
fastmcp install gemini-cli tool-mcps/boltzgen_mcp/src/boltzgen_mcp.py --python tool-mcps/boltzgen_mcp/env/bin/python
```
### Call MCP service
1. Execute a binder design job give a target pdb structure
```markdown
Please design binder for target 1g13prot with config file @examples/case2_binder_design/1g13prot.yaml using the boltzgen_mcp. Use the protein-anything protocol and save it to @examples/case2_binder_design/results.

After submitting the job, please query status every 2 minutes until the task finishes.

Please convert the relative path to absolution path before calling the MCP servers.
```

2. Execute a nanobody design job
```markdown
Please design a nanobody binder using the nanobody-anything protocol with config @examples/case3_nanobody_design/penguinpox.yaml. Save results to @examples/case3_nanobody_design/results.

After submitting the job, please query status every 2 minutes until the task finishes.
Please convert the relative path to absolution path before calling the MCP servers.
```