#!/usr/bin/env python3
"""
Test that the MCP server imports correctly and all dependencies are available.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_imports():
    """Test that all modules import correctly."""
    try:
        print("Testing imports...")

        # Test job manager import
        from jobs.manager import job_manager, JobStatus
        print("✅ Job manager imports")

        # Test server import
        from server import mcp
        print("✅ MCP server imports")

        # Test that job manager is initialized
        assert hasattr(job_manager, 'submit_job')
        assert hasattr(job_manager, 'get_job_status')
        print("✅ Job manager has expected methods")

        # Test that MCP server has tools
        assert hasattr(mcp, '_tools')
        tools_count = len(mcp._tools)
        print(f"✅ MCP server has {tools_count} tools registered")

        # List tool names
        tool_names = list(mcp._tools.keys())
        print(f"\nRegistered tools:")
        for tool_name in sorted(tool_names):
            print(f"  - {tool_name}")

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

        missing_tools = [tool for tool in expected_tools if tool not in tool_names]
        if missing_tools:
            print(f"\n❌ Missing tools: {missing_tools}")
            return False
        else:
            print(f"\n✅ All {len(expected_tools)} expected tools are registered")

        return True

    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_paths():
    """Test that required paths exist."""
    try:
        print("\nTesting paths...")

        # Test scripts directory
        scripts_dir = Path(__file__).parent.parent / "scripts"
        if scripts_dir.exists():
            print(f"✅ Scripts directory exists: {scripts_dir}")
        else:
            print(f"❌ Scripts directory missing: {scripts_dir}")
            return False

        # Test required scripts
        required_scripts = [
            'protein_binder_design.py',
            'peptide_binder_design.py',
            'check_config.py',
            'run_boltzgen.py'
        ]

        for script in required_scripts:
            script_path = scripts_dir / script
            if script_path.exists():
                print(f"✅ {script} exists")
            else:
                print(f"❌ {script} missing")
                return False

        # Test environment directory
        env_dir = Path(__file__).parent.parent / "env"
        if env_dir.exists():
            print(f"✅ Environment directory exists: {env_dir}")
        else:
            print(f"⚠️  Environment directory missing: {env_dir}")

        return True

    except Exception as e:
        print(f"❌ Path test failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("BoltzGen MCP Server Validation")
    print("=" * 40)

    tests = [
        ("Imports", test_imports),
        ("Paths", test_paths)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{'-' * 20}")
        result = test_func()
        results.append((test_name, result))

    print(f"\n{'='*40}")
    print("Validation Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")

    if passed == total:
        print("\n🎉 MCP server is ready for use!")
    else:
        print("\n⚠️  Some issues found - please review above")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)