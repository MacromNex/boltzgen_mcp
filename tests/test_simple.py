#!/usr/bin/env python3
"""
Simple test that the MCP server can be imported and started.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_basic_functionality():
    """Test basic server functionality."""
    try:
        print("Testing basic imports...")

        # Test job manager import
        from jobs.manager import job_manager, JobStatus
        print("✅ Job manager imports successfully")

        # Test server import
        from server import mcp
        print("✅ MCP server imports successfully")

        # Test job manager basic functionality
        jobs = job_manager.list_jobs()
        print(f"✅ Job manager works - found {jobs['total']} existing jobs")

        # Test that we can introspect the server object
        print(f"✅ MCP server type: {type(mcp)}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_basic_functionality()
    if success:
        print("\n🎉 Basic functionality test passed!")
    else:
        print("\n❌ Basic functionality test failed!")
    sys.exit(0 if success else 1)