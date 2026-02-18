# Step 3: Use Cases Report

## Scan Information
- **Scan Date**: 2025-12-21
- **Filter Applied**: Protein design using BoltzGen, the mcp is working and in tool-mcps/boltzgen_mcp/src/boltzgen_mcp.py, please extract the relevant information following the workflow
- **Python Version**: 3.12.12
- **Environment Strategy**: Single environment (./env)
- **MCP Framework**: FastMCP 2.13.3

## Use Cases Identified

### UC-001: Protein Binder Design
- **Description**: Design proteins that bind to protein targets using general protocol
- **Script Path**: `examples/use_case_1_protein_binder_design.py`
- **Protocol**: `protein-anything` (default)
- **Complexity**: Medium
- **Priority**: High
- **Environment**: `./env`
- **Source**: `src/tools/boltzgen_design.py`, `example/vanilla_protein/1g13prot.yaml`

**Inputs:**
| Name | Type | Description | Parameter |
|------|------|-------------|----------|
| config | file | YAML configuration file | --config |
| output | directory | Output directory path | --output |
| num_designs | integer | Number of designs to generate | --num_designs |
| budget | integer | Final diverse designs count | --budget |
| cuda_device | string | CUDA device ID | --cuda_device |

**Outputs:**
| Name | Type | Description |
|------|------|-------------|
| pdb_files | files | 3D structure files of designed proteins |
| log_files | files | Execution logs |
| statistics | json | Design generation statistics |

**Example Usage:**
```bash
python examples/use_case_1_protein_binder_design.py --config examples/data/1g13prot.yaml --output examples/results/protein_binder_1g13 --num_designs 10 --budget 2
```

**Example Data**: `examples/data/1g13prot.yaml`, `examples/data/1g13.cif`

---

### UC-002: Peptide Binder Design
- **Description**: Design peptides (including cyclic) that bind to protein targets with cysteine filtering
- **Script Path**: `examples/use_case_2_peptide_binder_design.py`
- **Protocol**: `peptide-anything`
- **Complexity**: Medium
- **Priority**: High
- **Environment**: `./env`
- **Source**: `src/tools/boltzgen_design.py`, `example/vanilla_peptide_with_target_binding_site/beetletert.yaml`

**Inputs:**
| Name | Type | Description | Parameter |
|------|------|-------------|----------|
| config | file | YAML configuration file | --config |
| output | directory | Output directory path | --output |
| num_designs | integer | Number of designs to generate | --num_designs |
| budget | integer | Final diverse designs count | --budget |
| alpha | float | Diversity vs quality tradeoff | --alpha |
| cuda_device | string | CUDA device ID | --cuda_device |

**Outputs:**
| Name | Type | Description |
|------|------|-------------|
| pdb_files | files | 3D structure files of designed peptides |
| log_files | files | Execution logs with peptide-specific filtering |

**Example Usage:**
```bash
python examples/use_case_2_peptide_binder_design.py --config examples/data/beetletert.yaml --output examples/results/peptide_binder --alpha 0.01
```

**Example Data**: `examples/data/beetletert.yaml`, `examples/data/5cqg.cif`

---

### UC-003: Protein-Small Molecule Interaction Design
- **Description**: Design proteins that bind to small molecules with affinity prediction
- **Script Path**: `examples/use_case_3_protein_small_molecule_design.py`
- **Protocol**: `protein-small_molecule`
- **Complexity**: Medium
- **Priority**: High
- **Environment**: `./env`
- **Source**: `src/tools/boltzgen_design.py`, `example/protein_binding_small_molecule/chorismite.yaml`

**Inputs:**
| Name | Type | Description | Parameter |
|------|------|-------------|----------|
| config | file | YAML configuration with ligand specification | --config |
| output | directory | Output directory path | --output |
| num_designs | integer | Number of designs to generate | --num_designs |
| budget | integer | Final diverse designs count | --budget |
| cuda_device | string | CUDA device ID | --cuda_device |

**Outputs:**
| Name | Type | Description |
|------|------|-------------|
| pdb_files | files | 3D structure files of designed proteins |
| affinity_predictions | files | Binding affinity prediction results |
| log_files | files | Execution logs |

**Example Usage:**
```bash
python examples/use_case_3_protein_small_molecule_design.py --config examples/data/chorismite.yaml --output examples/results/small_molecule_binder
```

**Example Data**: `examples/data/chorismite.yaml` (uses TSA ligand CCD code)

---

### UC-004: Nanobody CDR Design
- **Description**: Design nanobody Complementarity Determining Regions with cysteine filtering
- **Script Path**: `examples/use_case_4_nanobody_design.py`
- **Protocol**: `nanobody-anything`
- **Complexity**: Medium
- **Priority**: High
- **Environment**: `./env`
- **Source**: `src/tools/boltzgen_design.py`, `example/nanobody/penguinpox.yaml`

**Inputs:**
| Name | Type | Description | Parameter |
|------|------|-------------|----------|
| config | file | YAML configuration with nanobody scaffolds | --config |
| output | directory | Output directory path | --output |
| num_designs | integer | Number of designs to generate | --num_designs |
| budget | integer | Final diverse designs count | --budget |
| cuda_device | string | CUDA device ID | --cuda_device |

**Outputs:**
| Name | Type | Description |
|------|------|-------------|
| pdb_files | files | 3D structure files of designed nanobodies |
| cdr_analysis | files | CDR loop analysis results |
| log_files | files | Execution logs |

**Example Usage:**
```bash
python examples/use_case_4_nanobody_design.py --config examples/data/penguinpox.yaml --output examples/results/nanobody_design
```

**Example Data**: `examples/data/penguinpox.yaml`, `examples/data/9bkq-assembly2.cif`

---

### UC-005: Antibody CDR Design
- **Description**: Design full antibody (Fab) Complementarity Determining Regions
- **Script Path**: `examples/use_case_5_antibody_design.py`
- **Protocol**: `antibody-anything`
- **Complexity**: Medium
- **Priority**: High
- **Environment**: `./env`
- **Source**: `src/tools/boltzgen_design.py`, custom simplified config

**Inputs:**
| Name | Type | Description | Parameter |
|------|------|-------------|----------|
| config | file | YAML configuration with antibody scaffolds | --config |
| output | directory | Output directory path | --output |
| num_designs | integer | Number of designs to generate | --num_designs |
| budget | integer | Final diverse designs count | --budget |
| cuda_device | string | CUDA device ID | --cuda_device |

**Outputs:**
| Name | Type | Description |
|------|------|-------------|
| pdb_files | files | 3D structure files of designed antibodies |
| fab_analysis | files | Heavy/light chain analysis |
| log_files | files | Execution logs |

**Example Usage:**
```bash
python examples/use_case_5_antibody_design.py --config examples/data/pdl1_simplified.yaml --output examples/results/antibody_design
```

**Example Data**: `examples/data/pdl1_simplified.yaml`, `examples/data/7rpz.cif`

---

## Additional MCP Integration Use Cases

### UC-MCP-001: Asynchronous Job Submission
- **Function**: `boltzgen_submit`
- **Description**: Submit BoltzGen jobs asynchronously with status monitoring
- **Source**: `src/tools/boltzgen_design.py:285`

### UC-MCP-002: Job Status Monitoring
- **Function**: `boltzgen_check_status`
- **Description**: Monitor submitted job progress and results
- **Source**: `src/tools/boltzgen_design.py:442`

### UC-MCP-003: Synchronous Execution
- **Function**: `boltzgen_run`
- **Description**: Run complete BoltzGen pipeline synchronously
- **Source**: `src/tools/boltzgen_design.py:145`

## Summary

| Metric | Count |
|--------|-------|
| **Core Use Cases Found** | 5 |
| **Scripts Created** | 5 |
| **High Priority** | 5 |
| **Medium Priority** | 0 |
| **Low Priority** | 0 |
| **MCP Functions** | 3 |
| **Demo Data Files** | 13 |
| **Example Configs** | 6 |

## Demo Data Index

| Source | Destination | Description |
|--------|-------------|-------------|
| `example/vanilla_protein/1g13prot.yaml` | `examples/data/1g13prot.yaml` | Protein binder design configuration |
| `example/vanilla_protein/1g13.cif` | `examples/data/1g13.cif` | Protein target structure |
| `example/vanilla_peptide_with_target_binding_site/beetletert.yaml` | `examples/data/beetletert.yaml` | Peptide binder with binding site |
| `example/vanilla_peptide_with_target_binding_site/5cqg.cif` | `examples/data/5cqg.cif` | Beetletert protein structure |
| `example/protein_binding_small_molecule/chorismite.yaml` | `examples/data/chorismite.yaml` | Small molecule binding design |
| `example/nanobody/penguinpox.yaml` | `examples/data/penguinpox.yaml` | Nanobody design configuration |
| `example/nanobody/9bkq-assembly2.cif` | `examples/data/9bkq-assembly2.cif` | Penguinpox target structure |
| `example/fab_targets/pdl1.yaml` | `examples/data/pdl1.yaml` | Original antibody design config |
| Custom creation | `examples/data/pdl1_simplified.yaml` | Simplified antibody design config |
| `example/7rpz.cif` | `examples/data/7rpz.cif` | Target structure for antibody design |
| `example/8r3a.cif` | `examples/data/8r3a.cif` | Additional protein structure |

## Protocol Coverage

| Protocol | Use Case | Features | Priority |
|----------|----------|----------|----------|
| `protein-anything` | UC-001 | General protein design, default protocol | High |
| `peptide-anything` | UC-002 | Cysteine filtering, optimized diversity | High |
| `protein-small_molecule` | UC-003 | Affinity prediction, ligand binding | High |
| `nanobody-anything` | UC-004 | CDR design, single-domain antibodies | High |
| `antibody-anything` | UC-005 | Full antibody design, heavy/light chains | High |

## Validation Status
- [x] All scripts are executable
- [x] All default configurations are valid
- [x] Demo data successfully copied and organized
- [x] Scripts include proper error handling and logging
- [x] Examples directory structure created
- [x] Integration with MCP framework verified
- [x] GPU support included in all scripts
- [x] Parameter validation implemented