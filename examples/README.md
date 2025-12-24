# BoltzGen MCP Examples

This directory contains standalone Python scripts demonstrating the 5 main BoltzGen protocols for protein design.

## Quick Start

All scripts can be run from the repository root directory:

```bash
# Activate the environment
mamba activate ./env

# Run any use case with default parameters
python examples/use_case_1_protein_binder_design.py
python examples/use_case_2_peptide_binder_design.py
python examples/use_case_3_protein_small_molecule_design.py
python examples/use_case_4_nanobody_design.py
python examples/use_case_5_antibody_design.py
```

## Use Cases Overview

| Script | Protocol | Description | Default Config | Output Dir |
|--------|----------|-------------|----------------|------------|
| `use_case_1_protein_binder_design.py` | `protein-anything` | General protein binder design | `examples/data/1g13prot.yaml` | `examples/results/protein_binder_1g13` |
| `use_case_2_peptide_binder_design.py` | `peptide-anything` | Peptide binder design (filters cysteines) | `examples/data/beetletert.yaml` | `examples/results/peptide_binder_beetletert` |
| `use_case_3_protein_small_molecule_design.py` | `protein-small_molecule` | Protein-small molecule interaction design | `examples/data/chorismite.yaml` | `examples/results/small_molecule_binder_chorismite` |
| `use_case_4_nanobody_design.py` | `nanobody-anything` | Nanobody CDR design (filters cysteines) | `examples/data/penguinpox.yaml` | `examples/results/nanobody_design_penguinpox` |
| `use_case_5_antibody_design.py` | `antibody-anything` | Antibody CDR design (filters cysteines) | `examples/data/pdl1_simplified.yaml` | `examples/results/antibody_design_pdl1` |

## Example Usage

### Basic Usage
```bash
# Run with default parameters (fast for testing)
python examples/use_case_1_protein_binder_design.py
```

### Custom Parameters
```bash
# Run with custom parameters
python examples/use_case_1_protein_binder_design.py \
    --config examples/data/1g13prot.yaml \
    --output examples/results/my_custom_run \
    --num_designs 50 \
    --budget 5 \
    --cuda_device 0
```

### Production Parameters
```bash
# Production run with more designs
python examples/use_case_1_protein_binder_design.py \
    --num_designs 10000 \
    --budget 30 \
    --cuda_device 0
```

## Configuration Files and Demo Data

### Configuration Files (`examples/data/`)

| File | Description | Target Structure |
|------|-------------|------------------|
| `1g13prot.yaml` | Protein binder design config | `1g13.cif` (protein target) |
| `beetletert.yaml` | Peptide binder with binding site | `5cqg.cif` (beetletert protein) |
| `chorismite.yaml` | Protein-small molecule design | TSA ligand (CCD code) |
| `penguinpox.yaml` | Nanobody design | `9bkq-assembly2.cif` (penguinpox target) |
| `pdl1_simplified.yaml` | Simplified antibody design | `7rpz.cif` (target structure) |

### Structure Files (`examples/data/`)

| File | Description | Used By |
|------|-------------|---------|
| `1g13.cif` | Protein target structure | `1g13prot.yaml` |
| `5cqg.cif` | Beetletert protein structure | `beetletert.yaml` |
| `9bkq-assembly2.cif` | Penguinpox target structure | `penguinpox.yaml` |
| `7rpz.cif` | Target structure for antibody design | `pdl1_simplified.yaml` |
| `8r3a.cif` | Additional protein structure | Available for custom configs |

## Parameter Guidelines

### Number of Designs (`--num_designs`)
- **Testing/Development**: 10-100 designs
- **Validation**: 1,000-5,000 designs
- **Production**: 10,000-60,000 designs

### Budget (`--budget`)
- **Testing**: 2-5 final designs
- **Production**: 30-100 final designs

### Alpha Parameter (`--alpha`, peptide protocol only)
- **Quality focus**: 0.0 (default)
- **Balanced**: 0.01-0.1
- **Diversity focus**: 1.0

## Expected Outputs

Each use case generates:
- **PDB files**: 3D structure files for each designed protein/peptide
- **Log files**: Detailed execution logs
- **Analysis files**: CSV/JSON files with design metrics (protocol-dependent)

## GPU Usage

All scripts support GPU acceleration:
```bash
# Use specific GPU
python examples/use_case_1_protein_binder_design.py --cuda_device 0

# Let BoltzGen auto-select GPU
python examples/use_case_1_protein_binder_design.py
```

## Troubleshooting

### Common Issues

1. **Config file not found**
   - Ensure you're running from the repository root
   - Check that demo data was copied correctly

2. **BoltzGen command not found**
   - Activate the conda environment: `mamba activate ./env`
   - Install BoltzGen: `pip install boltzgen`

3. **GPU memory errors**
   - Reduce `--num_designs` parameter
   - Use specific GPU: `--cuda_device 0`

4. **Port conflicts**
   - Scripts use port 29500 by default for torch.distributed
   - Modify the port in the script if needed

### Validation

Test your setup with a minimal run:
```bash
python examples/use_case_1_protein_binder_design.py --num_designs 2 --budget 1
```

## Integration with MCP

These standalone scripts demonstrate the same functionality as the BoltzGen MCP server. To use via MCP:

```python
# Via MCP tools
result = boltzgen_run(
    config="examples/data/1g13prot.yaml",
    output="examples/results/mcp_test",
    protocol="protein-anything",
    num_designs=10,
    budget=2
)
```

## Protocol Details

### protein-anything
- **Best for**: General protein binder design
- **Features**: Default protocol, broad applicability
- **Output**: PDB structures of designed proteins

### peptide-anything
- **Best for**: Peptide and cyclic peptide design
- **Features**: Cysteine filtering, optimized diversity
- **Output**: PDB structures of designed peptides

### protein-small_molecule
- **Best for**: Enzyme design, small molecule binding
- **Features**: Binding affinity prediction included
- **Output**: PDB structures + affinity predictions

### nanobody-anything
- **Best for**: Single-domain antibody design
- **Features**: CDR-focused, cysteine filtering
- **Output**: Nanobody structures with designed CDRs

### antibody-anything
- **Best for**: Full antibody (Fab) design
- **Features**: Heavy/light chain design, cysteine filtering
- **Output**: Antibody structures with designed CDRs