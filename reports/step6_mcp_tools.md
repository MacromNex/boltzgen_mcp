# Step 6: MCP Tools Documentation

## Server Information
- **Server Name**: boltzgen
- **Version**: 1.0.0
- **Created Date**: 2025-12-21
- **Server Path**: `src/server.py`
- **Framework**: FastMCP 2.13.3

## Job Management Tools

| Tool | Description |
|------|-------------|
| `get_job_status` | Check job progress and status |
| `get_job_result` | Get completed job results and output files |
| `get_job_log` | View job execution logs with optional tail |
| `cancel_job` | Cancel running job |
| `list_jobs` | List all jobs with optional status filtering |

## Sync Tools (Fast Operations < 5 min)

| Tool | Description | Source Script | Est. Runtime |
|------|-------------|---------------|--------------|
| `validate_config` | Validate BoltzGen configuration files | `scripts/check_config.py` | ~10-30 sec |

### Tool Details

#### validate_config
- **Description**: Validate a BoltzGen configuration file quickly without running the full pipeline
- **Source Script**: `scripts/check_config.py`
- **Estimated Runtime**: ~10-30 seconds

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| config_file | str | Yes | - | Path to BoltzGen YAML configuration file |
| verbose | bool | No | False | Enable verbose validation output |

**Example:**
```
Use validate_config with config_file "examples/data/1g13prot.yaml"
```

**Returns:**
```json
{
  "status": "success",
  "config_file": "examples/data/1g13prot.yaml",
  "valid": true,
  "stdout": "Configuration validated successfully",
  "stderr": "",
  "return_code": 0
}
```

---

## Submit Tools (Long Operations > 5 min)

| Tool | Description | Source Script | Est. Runtime | Batch Support |
|------|-------------|---------------|--------------|---------------|
| `submit_protein_binder_design` | Design protein binders | `scripts/protein_binder_design.py` | 5-20 min | ✅ Yes |
| `submit_peptide_binder_design` | Design peptide binders | `scripts/peptide_binder_design.py` | 5-15 min | ✅ Yes |
| `submit_generic_boltzgen` | Run any BoltzGen protocol | `scripts/run_boltzgen.py` | 5-30 min | ❌ No |
| `submit_batch_protein_design` | Batch protein design | Generated batch script | Variable | ✅ Native |

### Tool Details

#### submit_protein_binder_design
- **Description**: Design protein binders using BoltzGen protein-anything protocol
- **Source Script**: `scripts/protein_binder_design.py`
- **Estimated Runtime**: 5-20 minutes (depends on design complexity)
- **Supports Batch**: ✅ Yes (via submit_batch_protein_design)

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| config_file | str | Yes | - | Path to BoltzGen YAML configuration file |
| output_dir | str | Yes | - | Directory to save design outputs |
| num_designs | int | No | 10 | Number of designs to generate |
| budget | int | No | 2 | Computational budget for design |
| cuda_device | str | No | None | CUDA device ID (auto-detected if None) |
| master_port | int | No | None | Port for distributed training |
| verbose | bool | No | True | Enable verbose logging |
| job_name | str | No | auto | Custom job name for tracking |

**Example:**
```
Submit protein binder design for examples/data/1g13prot.yaml
```

---

#### submit_peptide_binder_design
- **Description**: Design peptide binders using BoltzGen peptide-anything protocol
- **Source Script**: `scripts/peptide_binder_design.py`
- **Estimated Runtime**: 5-15 minutes (depends on design complexity)
- **Supports Batch**: ✅ Yes (via custom batch script)

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| config_file | str | Yes | - | Path to BoltzGen YAML configuration file |
| output_dir | str | Yes | - | Directory to save design outputs |
| num_designs | int | No | 10 | Number of designs to generate |
| budget | int | No | 2 | Computational budget for design |
| alpha | float | No | None | Diversity parameter (0.0=quality, 1.0=diversity) |
| cuda_device | str | No | None | CUDA device ID (auto-detected if None) |
| master_port | int | No | None | Port for distributed training |
| verbose | bool | No | True | Enable verbose logging |
| job_name | str | No | auto | Custom job name for tracking |

**Example:**
```
Submit peptide binder design for examples/data/beetletert.yaml with alpha 0.01
```

---

#### submit_generic_boltzgen
- **Description**: Run any BoltzGen protocol with custom parameters
- **Source Script**: `scripts/run_boltzgen.py`
- **Estimated Runtime**: 5-30 minutes (highly variable based on protocol)
- **Supports Batch**: ❌ No (use specific tools for batch processing)

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| config_file | str | Yes | - | Path to BoltzGen YAML configuration file |
| output_dir | str | Yes | - | Directory to save outputs |
| protocol | str | No | protein-anything | BoltzGen protocol name |
| num_designs | int | No | 10 | Number of designs to generate |
| budget | int | No | 2 | Computational budget for design |
| cuda_device | str | No | None | CUDA device ID (auto-detected if None) |
| master_port | int | No | None | Port for distributed training |
| verbose | bool | No | True | Enable verbose logging |
| job_name | str | No | auto | Custom job name for tracking |

**Example:**
```
Submit generic BoltzGen with protocol "protein-anything" for custom.yaml
```

---

#### submit_batch_protein_design
- **Description**: Process multiple protein targets in a single batch job
- **Source Script**: Generated batch processing script
- **Estimated Runtime**: Variable (num_configs × avg_time_per_design)
- **Supports Batch**: ✅ Native batch processing

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| config_files | List[str] | Yes | - | List of BoltzGen YAML configuration files |
| output_base_dir | str | Yes | - | Base directory (subdirs created per config) |
| num_designs | int | No | 10 | Number of designs per target |
| budget | int | No | 2 | Computational budget per design |
| cuda_device | str | No | None | CUDA device ID (auto-detected if None) |
| job_name | str | No | auto | Custom job name for tracking |

**Example:**
```
Submit batch protein design for ["config1.yaml", "config2.yaml", "config3.yaml"]
```

---

## Workflow Examples

### Quick Configuration Validation (Sync)
```
Use validate_config with config_file "examples/data/1g13prot.yaml"
→ Returns validation results immediately
```

### Single Protein Design (Submit API)
```
1. Submit: submit_protein_binder_design with config_file "examples/data/1g13prot.yaml", output_dir "results/protein_design"
   → Returns: {"job_id": "abc123", "status": "submitted"}

2. Check: get_job_status with job_id "abc123"
   → Returns: {"status": "running", "started_at": "2025-12-21T10:00:00"}

3. Monitor: get_job_log with job_id "abc123", tail 20
   → Returns: {"log_lines": ["Step 1/6: Design...", "Step 2/6: Inverse folding..."]}

4. Result: get_job_result with job_id "abc123"
   → Returns: {"status": "success", "output_directory": "results/protein_design", "output_files": ["design_1.cif", "design_2.cif"]}
```

### Peptide Design with Custom Parameters (Submit API)
```
1. Submit: submit_peptide_binder_design with:
   - config_file "examples/data/beetletert.yaml"
   - output_dir "results/peptide_design"
   - alpha 0.01 (quality-focused)
   - num_designs 20

2. Track progress with get_job_status and get_job_log as above

3. Get results with get_job_result when completed
```

### Batch Processing Multiple Targets (Submit API)
```
1. Submit: submit_batch_protein_design with:
   - config_files ["target1.yaml", "target2.yaml", "target3.yaml"]
   - output_base_dir "results/batch_design"
   - num_designs 5
   - budget 1 (for faster processing)

2. Monitor: get_job_log with job_id to see progress through all targets

3. Result: Each target will have its own subdirectory in output_base_dir
```

### Job Management
```
# List all jobs
list_jobs
→ Returns: {"jobs": [{"job_id": "abc123", "status": "completed", "job_name": "protein_binder_1g13prot"}]}

# List only running jobs
list_jobs with status "running"

# Cancel a job if needed
cancel_job with job_id "def456"
```

## Error Handling

All tools return structured error responses:

```json
{
  "status": "error",
  "error": "Detailed error message",
  "job_id": "abc123" // if applicable
}
```

Common error scenarios:
- **File not found**: Configuration file doesn't exist
- **Invalid configuration**: YAML parsing or validation errors
- **BoltzGen not installed**: Command not found in environment
- **CUDA errors**: GPU memory issues or driver problems
- **Port conflicts**: master_port already in use
- **Job not found**: Invalid job_id provided

## Performance Notes

### Resource Requirements
- **Memory**: 8-16 GB RAM recommended
- **GPU**: 7-8 GB VRAM for typical designs
- **Disk**: 1-5 GB per design (temporary and output files)
- **Network**: Port range 29500-29600 for distributed training

### Optimization Tips
- **Reduce budget**: Use budget=1 for faster (lower quality) designs
- **Specify CUDA device**: Use cuda_device="0" to avoid device selection overhead
- **Batch processing**: More efficient than individual jobs for multiple targets
- **Monitor logs**: Use get_job_log to check progress and identify bottlenecks

## Integration Examples

### With Claude Desktop
Add to MCP configuration:
```json
{
  "mcpServers": {
    "boltzgen": {
      "command": "mamba",
      "args": ["run", "-p", "./env", "python", "src/server.py"]
    }
  }
}
```

### Programmatic Usage
```python
# Example client code (hypothetical)
import mcp_client

client = mcp_client.connect("boltzgen")

# Submit job
result = client.call_tool("submit_protein_binder_design", {
    "config_file": "my_target.yaml",
    "output_dir": "results/"
})

job_id = result["job_id"]

# Poll for completion
while True:
    status = client.call_tool("get_job_status", {"job_id": job_id})
    if status["status"] == "completed":
        break
    time.sleep(30)

# Get results
result = client.call_tool("get_job_result", {"job_id": job_id})
print(f"Output files: {result['output_files']}")
```