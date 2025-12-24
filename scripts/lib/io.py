"""
Shared I/O functions for MCP scripts.

These are extracted and simplified from repo code to minimize dependencies.
"""

from pathlib import Path
from typing import Union, Any, Dict
import json

def load_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Load JSON configuration file."""
    with open(file_path) as f:
        return json.load(f)

def save_json(data: Dict[str, Any], file_path: Union[str, Path]) -> None:
    """Save data to JSON file."""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def validate_config_file(config_path: Path) -> bool:
    """Validate config file exists and is valid."""
    if config_path.is_dir():
        return False
    if not config_path.exists():
        return False
    return True

def count_structure_files(output_path: Path) -> Dict[str, int]:
    """Count generated structure files."""
    if not output_path.exists():
        return {"cif": 0, "pdb": 0, "total": 0}

    cif_files = list(output_path.glob("*.cif"))
    pdb_files = list(output_path.glob("*.pdb"))

    return {
        "cif": len(cif_files),
        "pdb": len(pdb_files),
        "total": len(cif_files) + len(pdb_files)
    }