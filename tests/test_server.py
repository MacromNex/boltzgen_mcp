#!/usr/bin/env python3
"""
Test script for BoltzGen MCP server functionality.
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from server import mcp

def test_server_tools():
    """Test that all expected tools are registered."""
    tools = mcp.list_tools()
    tool_names = [tool['name'] for tool in tools]

    print("Available tools:")
    for tool in tools:
        print(f"  - {tool['name']}: {tool.get('description', 'No description')}")

    # Expected tools
    expected_tools = [
        'get_job_status',
        'get_job_result',
        'get_job_log',
        'cancel_job',
        'list_jobs',
        'validate_config',
        'submit_protein_binder_design',
        'submit_peptide_binder_design',
        'submit_generic_boltzgen',
        'submit_batch_protein_design'
    ]

    print(f"\nChecking for {len(expected_tools)} expected tools...")
    for tool in expected_tools:
        if tool in tool_names:
            print(f"  ✅ {tool}")
        else:
            print(f"  ❌ {tool} - MISSING")

    print(f"\nTotal tools found: {len(tool_names)}")
    return len(expected_tools) == len([t for t in expected_tools if t in tool_names])

def test_validate_config():
    """Test config validation with a dummy file."""
    # Create a dummy config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
# Dummy BoltzGen config for testing
target: dummy.pdb
output: results/
""")
        config_path = f.name

    try:
        # Test config validation (should fail gracefully with dummy config)
        result = mcp.call_tool('validate_config', {
            'config_file': config_path,
            'verbose': True
        })

        print(f"\nConfig validation test result: {result}")

        # Should return a structured response
        assert 'status' in result
        assert 'config_file' in result
        return True

    except Exception as e:
        print(f"Config validation test failed: {e}")
        return False
    finally:
        Path(config_path).unlink(missing_ok=True)

def test_job_listing():
    """Test job listing functionality."""
    try:
        result = mcp.call_tool('list_jobs', {})
        print(f"\nJob listing test result: {result}")

        assert 'status' in result
        assert result['status'] == 'success'
        assert 'jobs' in result
        assert 'total' in result

        print(f"Found {result['total']} existing jobs")
        return True

    except Exception as e:
        print(f"Job listing test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing BoltzGen MCP Server")
    print("=" * 40)

    tests = [
        ("Tool Registration", test_server_tools),
        ("Config Validation", test_validate_config),
        ("Job Listing", test_job_listing)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\nRunning {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{test_name}: {'✅ PASSED' if result else '❌ FAILED'}")
        except Exception as e:
            print(f"{test_name}: ❌ ERROR - {e}")
            results.append((test_name, False))

    print(f"\n{'='*40}")
    print("Test Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)