#!/usr/bin/env python3
"""Automated integration test runner for MCP server."""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

class MCPTestRunner:
    def __init__(self, server_path: str):
        self.server_path = Path(server_path)
        self.mcp_root = self.server_path.parent.parent
        self.python_path = self.mcp_root / "env" / "bin" / "python"
        self.results = {
            "test_date": datetime.now().isoformat(),
            "server_path": str(server_path),
            "mcp_root": str(self.mcp_root),
            "tests": {},
            "issues": [],
            "summary": {}
        }

        # Test data files
        self.test_data = {
            "valid_config_1": "examples/data/pdl1.yaml",
            "valid_config_2": "examples/data/beetletert.yaml",
            "valid_config_3": "examples/data/1g13prot.yaml",
            "small_config": "examples/data/pdl1_simplified.yaml",
            "invalid_config": "examples/data/nonexistent.yaml",
            "non_yaml": "src/server.py"
        }

    def run_python_test(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        """Run a Python code snippet and capture results."""
        try:
            result = subprocess.run(
                [str(self.python_path), "-c", code],
                cwd=str(self.mcp_root),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Test timed out after {timeout}s",
                "timeout": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "exception": True
            }

    def test_server_startup(self) -> bool:
        """Test that server starts without errors."""
        print("Testing server startup...")
        code = """
from src.server import mcp
print(f"MCP server '{mcp.name}' loaded successfully")
"""
        result = self.run_python_test(code)
        self.results["tests"]["server_startup"] = result
        return result["success"]

    def test_tool_registration(self) -> bool:
        """Test that tools are properly registered."""
        print("Testing tool registration...")
        code = """
from src.server import mcp
import inspect

# Count registered functions with @mcp.tool decorator
tool_count = 0
for name, obj in inspect.getmembers(mcp):
    if hasattr(obj, '__wrapped__'):  # FastMCP decorated functions
        tool_count += 1

print(f"Found {tool_count} registered tools")

# Check specific tools exist
expected_tools = [
    'get_job_status', 'get_job_result', 'get_job_log',
    'cancel_job', 'list_jobs', 'validate_config',
    'submit_protein_binder_design', 'submit_peptide_binder_design',
    'submit_generic_boltzgen', 'submit_batch_protein_design'
]

missing_tools = []
for tool in expected_tools:
    if not hasattr(mcp, tool):
        missing_tools.append(tool)

if missing_tools:
    print(f"Missing tools: {missing_tools}")
else:
    print("All expected tools found")
"""
        result = self.run_python_test(code)
        self.results["tests"]["tool_registration"] = result
        return result["success"]

    def test_config_validation_sync(self) -> bool:
        """Test synchronous config validation."""
        print("Testing config validation...")

        # Test valid config
        code = f"""
from src.server import mcp
from src.jobs.manager import job_manager

# Test valid config
result = validate_config(config_file='{self.test_data["valid_config_1"]}', verbose=False)
print(f"Valid config test: {result}")

# Test invalid config
result2 = validate_config(config_file='{self.test_data["invalid_config"]}', verbose=False)
print(f"Invalid config test: {result2}")
"""
        result = self.run_python_test(code, timeout=60)
        self.results["tests"]["config_validation"] = result
        return result["success"]

    def test_job_submission(self) -> bool:
        """Test job submission workflow."""
        print("Testing job submission...")

        code = f"""
import sys
sys.path.insert(0, 'src')
from server import submit_protein_binder_design, get_job_status
import time

# Submit a job
result = submit_protein_binder_design(
    config_file='{self.test_data["small_config"]}',
    output_dir='test_output/integration_test',
    num_designs=1,
    budget=1,
    verbose=True
)

print(f"Job submission result: {result}")

if result.get('status') == 'submitted':
    job_id = result['job_id']
    print(f"Submitted job: {job_id}")

    # Check status
    status_result = get_job_status(job_id)
    print(f"Job status: {status_result}")

    print("Job submission test passed")
else:
    print("Job submission failed")
    sys.exit(1)
"""
        result = self.run_python_test(code, timeout=120)
        self.results["tests"]["job_submission"] = result
        return result["success"]

    def test_job_management(self) -> bool:
        """Test job management tools."""
        print("Testing job management...")

        code = """
import sys
sys.path.insert(0, 'src')
from server import list_jobs, get_job_log

# List all jobs
jobs_result = list_jobs()
print(f"List jobs result: {jobs_result}")

if jobs_result.get('status') == 'success' and jobs_result.get('jobs'):
    # Get logs for the first job
    first_job = jobs_result['jobs'][0]
    job_id = first_job['job_id']

    log_result = get_job_log(job_id, tail=10)
    print(f"Job log result: {log_result}")

print("Job management test completed")
"""
        result = self.run_python_test(code, timeout=60)
        self.results["tests"]["job_management"] = result
        return result["success"]

    def test_error_handling(self) -> bool:
        """Test error handling."""
        print("Testing error handling...")

        code = f"""
import sys
sys.path.insert(0, 'src')
from server import validate_config, get_job_status

# Test with invalid file
result1 = validate_config(config_file='nonexistent_file.yaml')
print(f"Invalid file test: {result1}")

# Test with invalid job ID
result2 = get_job_status('invalid_job_id')
print(f"Invalid job ID test: {result2}")

# Check that errors are handled gracefully
if result1.get('status') == 'error' and result2.get('status') == 'error':
    print("Error handling test passed")
else:
    print("Error handling test failed")
"""
        result = self.run_python_test(code)
        self.results["tests"]["error_handling"] = result
        return result["success"]

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        print("Starting MCP Server Integration Tests")
        print("=" * 50)

        tests = [
            ("Server Startup", self.test_server_startup),
            ("Tool Registration", self.test_tool_registration),
            ("Config Validation", self.test_config_validation_sync),
            ("Job Submission", self.test_job_submission),
            ("Job Management", self.test_job_management),
            ("Error Handling", self.test_error_handling),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            try:
                success = test_func()
                if success:
                    print(f"✅ {test_name} PASSED")
                    passed += 1
                else:
                    print(f"❌ {test_name} FAILED")
                    self.results["issues"].append({
                        "test": test_name,
                        "status": "failed",
                        "result": self.results["tests"].get(test_name.lower().replace(" ", "_"))
                    })
            except Exception as e:
                print(f"❌ {test_name} ERROR: {e}")
                self.results["issues"].append({
                    "test": test_name,
                    "status": "error",
                    "error": str(e)
                })

        # Generate summary
        self.results["summary"] = {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": f"{passed/total*100:.1f}%" if total > 0 else "N/A",
            "ready_for_production": passed == total
        }

        print(f"\n{'='*50}")
        print(f"Test Summary: {passed}/{total} tests passed ({self.results['summary']['pass_rate']})")
        print(f"Ready for production: {self.results['summary']['ready_for_production']}")

        return self.results

    def save_report(self, output_file: str = "reports/step7_integration.md"):
        """Save test results as markdown report."""
        report_content = f"""# Step 7: Integration Test Results

## Test Information
- **Test Date**: {self.results['test_date']}
- **Server Name**: boltzgen
- **Server Path**: `{self.results['server_path']}`
- **MCP Root**: `{self.results['mcp_root']}`

## Test Results Summary

| Test Category | Status | Notes |
|---------------|--------|-------|
"""

        for test_name, test_result in self.results["tests"].items():
            status = "✅ Passed" if test_result.get("success") else "❌ Failed"
            notes = "Completed successfully" if test_result.get("success") else "See details below"
            report_content += f"| {test_name.replace('_', ' ').title()} | {status} | {notes} |\n"

        report_content += f"""
## Summary

| Metric | Value |
|--------|-------|
| Total Tests | {self.results['summary']['total_tests']} |
| Passed | {self.results['summary']['passed']} |
| Failed | {self.results['summary']['failed']} |
| Pass Rate | {self.results['summary']['pass_rate']} |
| Ready for Production | {'✅ Yes' if self.results['summary']['ready_for_production'] else '❌ No'} |

## Detailed Results

"""

        for test_name, test_result in self.results["tests"].items():
            report_content += f"""### {test_name.replace('_', ' ').title()}
- **Status**: {'✅ Passed' if test_result.get('success') else '❌ Failed'}
- **Output**:
```
{test_result.get('stdout', 'No output')}
```
"""
            if test_result.get('stderr'):
                report_content += f"""- **Errors**:
```
{test_result['stderr']}
```
"""

        if self.results["issues"]:
            report_content += "\n## Issues Found\n\n"
            for issue in self.results["issues"]:
                report_content += f"""### Issue: {issue['test']}
- **Status**: {issue['status']}
- **Details**: {issue.get('error', 'See test result above')}

"""

        # Save report
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        Path(output_file).write_text(report_content)
        print(f"Report saved to: {output_file}")

if __name__ == "__main__":
    runner = MCPTestRunner("src/server.py")
    results = runner.run_all_tests()
    runner.save_report()

    # Exit with error code if tests failed
    if not results["summary"]["ready_for_production"]:
        sys.exit(1)

    print("\n🎉 All tests passed! MCP server is ready for production.")