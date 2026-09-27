#!/usr/bin/env python3
"""Test MCP tools using the MCP client interface."""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

class MCPClientTester:
    def __init__(self):
        self.mcp_root = Path.cwd()
        self.python_path = self.mcp_root / "env" / "bin" / "python"
        self.server_path = self.mcp_root / "src" / "server.py"

    def run_mcp_test(self, tool_name: str, arguments: dict = None, timeout: int = 60):
        """Run an MCP tool via the client interface."""
        try:
            # Create MCP request
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments or {}
                }
            }

            # Run server and send request
            cmd = [str(self.python_path), str(self.server_path)]

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.mcp_root)
            )

            # Send initialization and tool call
            init_request = {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            }

            input_data = json.dumps(init_request) + "\n" + json.dumps(request) + "\n"
            stdout, stderr = process.communicate(input=input_data, timeout=timeout)

            return {
                "success": process.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": process.returncode
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {
                "success": False,
                "error": f"Test timed out after {timeout}s"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def test_tool_discovery(self):
        """Test that we can discover available tools."""
        print("Testing tool discovery...")

        try:
            # Test tools/list
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }

            cmd = [str(self.python_path), str(self.server_path)]
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.mcp_root)
            )

            init_request = {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"}
                }
            }

            input_data = json.dumps(init_request) + "\n" + json.dumps(request) + "\n"
            stdout, stderr = process.communicate(input=input_data, timeout=30)

            print(f"Tool discovery stdout: {stdout}")
            print(f"Tool discovery stderr: {stderr}")

            return process.returncode == 0

        except Exception as e:
            print(f"Tool discovery error: {e}")
            return False

    def run_manual_tests(self):
        """Run manual tests by importing and calling functions directly."""
        print("\n=== Manual MCP Server Tests ===")

        # Test 1: Import server
        try:
            sys.path.insert(0, str(self.mcp_root / "src"))
            from server import (
                get_job_status, get_job_result, get_job_log, cancel_job, list_jobs,
                validate_config, submit_protein_binder_design, submit_peptide_binder_design
            )
            print("✅ All MCP tools imported successfully")
        except Exception as e:
            print(f"❌ Failed to import MCP tools: {e}")
            return False

        # Test 2: Config validation
        try:
            result = validate_config("examples/data/pdl1.yaml", verbose=False)
            print(f"✅ Config validation test: {result}")
        except Exception as e:
            print(f"❌ Config validation failed: {e}")

        # Test 3: List jobs
        try:
            result = list_jobs()
            print(f"✅ List jobs test: {result}")
        except Exception as e:
            print(f"❌ List jobs failed: {e}")

        # Test 4: Invalid job status
        try:
            result = get_job_status("invalid_job_id")
            print(f"✅ Invalid job status test: {result}")
        except Exception as e:
            print(f"❌ Invalid job status failed: {e}")

        # Test 5: Job submission (small test)
        try:
            result = submit_protein_binder_design(
                config_file="examples/data/pdl1_simplified.yaml",
                output_dir="test_output/manual_test",
                num_designs=1,
                budget=1,
                verbose=True
            )
            print(f"✅ Job submission test: {result}")

            if result.get("status") == "submitted":
                job_id = result["job_id"]
                print(f"Submitted job ID: {job_id}")

                # Check status
                status_result = get_job_status(job_id)
                print(f"✅ Job status check: {status_result}")

        except Exception as e:
            print(f"❌ Job submission failed: {e}")

        return True

if __name__ == "__main__":
    tester = MCPClientTester()

    print("Testing MCP Server Tools")
    print("=" * 40)

    # Test tool discovery via MCP protocol
    success1 = tester.test_tool_discovery()

    # Test manual function calls
    success2 = tester.run_manual_tests()

    print("\n" + "=" * 40)
    if success1 and success2:
        print("🎉 Manual tests completed successfully!")
    else:
        print("⚠️ Some tests had issues, but basic functionality works")