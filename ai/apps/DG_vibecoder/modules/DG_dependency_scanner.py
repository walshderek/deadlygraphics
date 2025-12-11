#!/usr/bin/env python3
"""
DG_dependency_scanner.py
Part of the Deadly Graphics Suite.

Purpose:
  Crawls a directory to identify:
  1. Python imports (via AST parsing)
  2. Package files (requirements.txt, pyproject.toml)
  3. GPU requirements (torch, tensorflow)
  4. System-level binary guesses (based on imports like cv2, soundfile)

Output:
  Generates a manifest.json in the target directory.
"""

import os
import sys
import json
import ast
import platform
from pathlib import Path

# ============================================================
# CONFIG / MAPPINGS
# ============================================================

# Map imports to Debian/Ubuntu system packages (heuristic)
SYS_PACKAGE_MAP = {
    "cv2": "libgl1-mesa-glx",
    "soundfile": "libsndfile1",
    "tk": "python3-tk",
    "PIL": "libjpeg-dev zlib1g-dev",  # Pillow deps
}

# Map imports to PyPI packages if names differ significantly
PYPI_MAP = {
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "sklearn": "scikit-learn",
    "yaml": "PyYAML",
    "bs4": "beautifulsoup4",
}

CRITICAL_GPU_MODULES = {"torch", "tensorflow", "jax", "diffusers"}

# ============================================================
# SCANNERS
# ============================================================

def get_imports_from_file(filepath):
    """
    Parses a .py file using AST to extract all imported module names.
    Returns a set of top-level module names.
    """
    imports = set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filepath.name)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
    except Exception as e:
        # verifying syntax errors or decoding issues don't crash the scanner
        print(f"[WARN] AST parse failed for {filepath.name}: {e}")
    
    return imports

def scan_directory(target_dir: Path):
    """
    Crawls the target directory for dependency clues.
    """
    scan_data = {
        "app_name": target_dir.name,
        "scan_time": None,  # Filled later
        "python_version_detected": platform.python_version(),
        "detected_imports": [],
        "config_files": [],
        "gpu_required": False,
        "suggested_system_packages": [],
        "suggested_pypi_packages": []
    }

    all_imports = set()
    has_requirements_txt = False
    has_pyproject = False

    # 1. Walk and Parse
    for root, _, files in os.walk(target_dir):
        if ".venv" in root or "__pycache__" in root or ".git" in root:
            continue
            
        for file in files:
            fpath = Path(root) / file
            
            # Check for config files
            if file == "requirements.txt":
                scan_data["config_files"].append("requirements.txt")
                has_requirements_txt = True
            elif file == "pyproject.toml":
                scan_data["config_files"].append("pyproject.toml")
                has_pyproject = True
            elif file == "environment.yml":
                scan_data["config_files"].append("environment.yml")

            # Parse Code
            if file.endswith(".py"):
                file_imports = get_imports_from_file(fpath)
                all_imports.update(file_imports)

    # 2. Filter Standard Library (Best Effort)
    # We compare against sys.stdlib_module_names if available (Py3.10+)
    if hasattr(sys, 'stdlib_module_names'):
        stdlib = sys.stdlib_module_names
        all_imports = {i for i in all_imports if i not in stdlib}
    
    # 3. Analyze Imports
    scan_data["detected_imports"] = sorted(list(all_imports))
    
    # Check GPU
    if not all_imports.isdisjoint(CRITICAL_GPU_MODULES):
        scan_data["gpu_required"] = True

    # Map to System Packages
    for mod in all_imports:
        if mod in SYS_PACKAGE_MAP:
            pkg = SYS_PACKAGE_MAP[mod]
            if pkg not in scan_data["suggested_system_packages"]:
                scan_data["suggested_system_packages"].append(pkg)

    # Map to PyPI (Simple mapping + identity)
    # This is a baseline; 'uv' or 'pip' will solve the rest.
    pypi_list = set()
    for mod in all_imports:
        mapped = PYPI_MAP.get(mod, mod)
        pypi_list.add(mapped)
    
    scan_data["suggested_pypi_packages"] = sorted(list(pypi_list))

    return scan_data

# ============================================================
# MAIN
# ============================================================

def main():
    if len(sys.argv) < 2:
        target_path = Path.cwd()
    else:
        target_path = Path(sys.argv[1]).resolve()

    if not target_path.exists():
        print(f"[ERROR] Path not found: {target_path}")
        sys.exit(1)

    print(f"[SCAN] Scanning: {target_path}")
    data = scan_directory(target_path)
    
    # Add timestamp
    from datetime import datetime
    data["scan_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Output Manifest
    manifest_path = target_path / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    print(f"[SUCCESS] Manifest generated: {manifest_path}")
    
    # Preview
    print("-" * 40)
    print(f" App: {data['app_name']}")
    print(f" GPU Required: {data['gpu_required']}")
    print(f" Imports Found: {len(data['detected_imports'])}")
    print("-" * 40)

if __name__ == "__main__":
    main()