#!/usr/bin/env python3
"""
DG_app_manager.py
Part of the Deadly Graphics Suite.

Purpose:
  Orchestrates the deployment of external AI applications (ComfyUI, OneTrainer, etc.).
  Implements the "Onion Model":
  - Layer 1: Git clone
  - Layer 2: UV-accelerated Virtual Environment
  - Layer 3: Dependency Installation
  - Layer 4: Integration (Scanner + Manifest)
"""

import os
import sys
import subprocess
import shutil
import json
from pathlib import Path

# Import our scanner (assuming it sits in the same modules/ folder)
try:
    from . import DG_dependency_scanner
except ImportError:
    # Fallback if run directly
    import DG_dependency_scanner

# ============================================================
# CONFIG
# ============================================================

UV_INSTALL_SCRIPT = "curl -LsSf https://astral.sh/uv/install.sh | sh"

class AppManager:
    def __init__(self, apps_root: Path):
        self.apps_root = apps_root
        self.uv_bin = self._find_uv()

    def _find_uv(self):
        """Locates 'uv' executable or returns None."""
        return shutil.which("uv")

    def ensure_uv(self):
        """Installs uv if missing."""
        if self.uv_bin:
            print(f"[OK] uv detected: {self.uv_bin}")
            return
        
        print("[INSTALL] Installing uv (The Accelerator)...")
        try:
            subprocess.run(UV_INSTALL_SCRIPT, shell=True, check=True)
            print("[SUCCESS] uv installed.")
            self.uv_bin = shutil.which("uv") # Refresh
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to install uv: {e}")
            raise

    def clone_repo(self, repo_url: str, app_name: str):
        """Clones a repository into apps_root/app_name."""
        target_dir = self.apps_root / app_name
        
        if target_dir.exists():
            print(f"[INFO] App directory exists: {target_dir}")
            # Optional: git pull logic could go here
            return target_dir
            
        print(f"[CLONE] Cloning {app_name} from {repo_url}...")
        subprocess.run(["git", "clone", repo_url, str(target_dir)], check=True)
        return target_dir

    def create_venv(self, app_dir: Path):
        """Creates a venv using uv."""
        venv_dir = app_dir / ".venv"
        if venv_dir.exists():
            print(f"[INFO] Venv exists: {venv_dir}")
            return venv_dir

        print(f"[VENV] Creating venv for {app_dir.name} using uv...")
        # uv venv .venv
        subprocess.run(["uv", "venv", ".venv"], cwd=app_dir, check=True)
        return venv_dir

    def install_deps(self, app_dir: Path):
        """Installs dependencies from requirements.txt using uv pip."""
        req_file = app_dir / "requirements.txt"
        if not req_file.exists():
            print(f"[WARN] No requirements.txt found in {app_dir.name}")
            return

        print(f"[INSTALL] Installing dependencies for {app_dir.name}...")
        # uv pip install -r requirements.txt
        # Note: We must activate the venv or point uv to it. 
        # uv automatically detects .venv in cwd.
        subprocess.run(["uv", "pip", "install", "-r", "requirements.txt"], cwd=app_dir, check=True)

    def scan_app(self, app_dir: Path):
        """Runs the DG_dependency_scanner on the new app."""
        print(f"[SCAN] Generating manifest for {app_dir.name}...")
        data = DG_dependency_scanner.scan_directory(app_dir)
        
        # Save manifest
        manifest_path = app_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[SUCCESS] Manifest saved to {manifest_path}")

    def deploy_app(self, app_name: str, repo_url: str):
        """Full deployment pipeline."""
        print(f"\n=== DEPLOYING: {app_name} ===")
        self.ensure_uv()
        
        app_dir = self.clone_repo(repo_url, app_name)
        self.create_venv(app_dir)
        self.install_deps(app_dir)
        self.scan_app(app_dir)
        
        print(f"=== DEPLOYMENT COMPLETE: {app_name} ===\n")

# ============================================================
# CLI ENTRYPOINT
# ============================================================

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 DG_app_manager.py <app_name> <repo_url>")
        print("Example: python3 DG_app_manager.py OneTrainer https://github.com/Nerogar/OneTrainer.git")
        return

    app_name = sys.argv[1]
    repo_url = sys.argv[2]
    
    # Apps root is one level up from this modules folder, then into 'apps' (or parallel)
    # Adjust as per Architecture. Assuming DG_vibecoder/apps_managed/
    root = Path(__file__).resolve().parent.parent
    apps_managed = root / "apps_managed"
    apps_managed.mkdir(exist_ok=True)
    
    manager = AppManager(apps_managed)
    manager.deploy_app(app_name, repo_url)

if __name__ == "__main__":
    main()