"""
General utility functions for MCP scripts.

These functions provide common functionality needed across multiple scripts.
"""

import logging
from typing import Dict, Any

def setup_simple_logging(verbose: bool = False) -> None:
    """Simple logging setup without external dependencies."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        level=level
    )

def log_info(message: str) -> None:
    """Simple info logging."""
    print(f"INFO: {message}")

def log_success(message: str) -> None:
    """Simple success logging."""
    print(f"SUCCESS: {message}")

def log_error(message: str) -> None:
    """Simple error logging."""
    print(f"ERROR: {message}")

def merge_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
    """Merge multiple configuration dictionaries, later ones override earlier."""
    result = {}
    for config in configs:
        if config:
            result.update(config)
    return result

def validate_parameters(params: Dict[str, Any], required: list = None, defaults: Dict[str, Any] = None) -> Dict[str, Any]:
    """Validate and set default parameters."""
    if required:
        for param in required:
            if param not in params or params[param] is None:
                raise ValueError(f"Required parameter missing: {param}")

    if defaults:
        for key, value in defaults.items():
            if key not in params or params[key] is None:
                params[key] = value

    return params

def format_execution_time(seconds: float) -> str:
    """Format execution time in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.1f}s"