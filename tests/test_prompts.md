# MCP Server Test Prompts for BoltzGen

## Tool Discovery Tests

### Prompt 1: List All Tools
"What MCP tools are available? Give me a brief description of each."

### Prompt 2: Tool Details
"Explain how to use the validate_config tool, including all parameters."

### Prompt 3: Job Management Tools
"What job management tools are available for tracking long-running tasks?"

## Sync Tool Tests

### Prompt 4: Basic Config Validation
"Use validate_config with config_file='examples/data/pdl1.yaml'"

### Prompt 5: Config Validation with Verbose
"Run validate_config on examples/data/beetletert.yaml with verbose=true"

### Prompt 6: Config Validation Error Handling
"Try running validate_config with a non-existent file '/fake/path.yaml'"

### Prompt 7: Config Validation Invalid File
"Try validate_config with config_file='src/server.py' (not a YAML file)"

## Submit API Tests

### Prompt 8: Submit Protein Binder Design
"Submit a protein binder design job using submit_protein_binder_design with config_file='examples/data/pdl1.yaml' and output_dir='test_output/protein_design'"

### Prompt 9: Submit Peptide Binder Design
"Submit a peptide binder design job with config_file='examples/data/1g13prot.yaml' and output_dir='test_output/peptide_design'"

### Prompt 10: Submit Generic BoltzGen
"Submit a generic BoltzGen job with config='examples/data/penguinpox.yaml', output_dir='test_output/generic', protocol='protein-anything'"

### Prompt 11: Check Job Status
"Check the status of job <job_id_from_previous_submit>"

### Prompt 12: Get Job Logs
"Show me the last 30 lines of logs for job <job_id>"

### Prompt 13: List All Jobs
"List all submitted jobs"

### Prompt 14: List Completed Jobs
"List all jobs with status 'completed'"

### Prompt 15: Get Job Results
"Get the results for job <job_id> if it's completed"

### Prompt 16: Cancel Running Job
"Cancel the job <job_id> if it's still running"

## Batch Processing Tests

### Prompt 17: Batch Protein Design
"Process multiple protein targets in batch using submit_batch_protein_design with config_files=['examples/data/pdl1.yaml', 'examples/data/beetletert.yaml'] and output_base_dir='test_output/batch'"

### Prompt 18: Batch Status Check
"Check the status of batch job <batch_job_id>"

### Prompt 19: Batch Results
"Get all results from the batch processing job <batch_job_id> when completed"

## Error Handling Tests

### Prompt 20: Invalid Config File
"Submit a protein binder design with an invalid config file 'nonexistent.yaml'"

### Prompt 21: Invalid Output Directory
"Submit a job with output_dir='/invalid/readonly/path'"

### Prompt 22: Missing Required Parameters
"Try submit_protein_binder_design without providing config_file"

### Prompt 23: Invalid Job ID
"Check status of job 'invalid_job_id'"

## Real-World End-to-End Scenarios

### Prompt 24: Full Workflow
"I want to design protein binders for PD-L1. First validate the config file examples/data/pdl1.yaml, then submit the design job with num_designs=5, and monitor its progress until completion."

### Prompt 25: Conditional Processing
"Check if the config file examples/data/chorismite.yaml is valid. If it is, submit a peptide binder design job. If not, explain what's wrong."

### Prompt 26: Error Recovery
"Submit a protein binder design job for examples/data/pdl1.yaml. If it fails, show me the error log and suggest what might be wrong."

### Prompt 27: Multiple Target Analysis
"I have multiple protein targets. First validate all these configs: examples/data/pdl1.yaml, examples/data/beetletert.yaml, examples/data/1g13prot.yaml. Then submit design jobs only for the valid ones."

### Prompt 28: Resource Management
"List all currently running jobs. If there are more than 2 running jobs, cancel the oldest one to free up resources."

### Prompt 29: Results Analysis
"Submit a design job for examples/data/pdl1_simplified.yaml. Once completed, show me the results including output files generated and any analysis metrics."

### Prompt 30: Troubleshooting
"Submit a job using submit_generic_boltzgen with config 'examples/data/chorismite.yaml'. If it fails or gets stuck, debug the issue by examining logs and checking the job status."

## Performance Tests

### Prompt 31: Concurrent Jobs
"Submit 3 different design jobs simultaneously and track their progress."

### Prompt 32: Job Queue Management
"Submit 5 jobs quickly, then list all jobs to see the queue status."

### Prompt 33: Resource Cleanup
"List all completed jobs older than the last submission and verify they have proper results."

## Expected Behavior Notes

- **Sync Tools**: Should complete within 30 seconds
- **Submit Tools**: Should return immediately with job_id
- **Job Status**: Should update from pending -> running -> completed/failed
- **Job Logs**: Should show real-time progress
- **Error Handling**: Should return structured error messages
- **File Paths**: Should handle both relative and absolute paths
- **Batch Processing**: Should handle multiple inputs sequentially
- **Cancellation**: Should properly terminate running processes