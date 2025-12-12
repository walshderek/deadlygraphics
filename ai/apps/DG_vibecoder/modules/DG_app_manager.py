#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import json
from pathlib import Path

# Try import scanner
try: from . import DG_dependency_scanner
except ImportError: import DG_dependency_scanner

# SUITES
DG_SUITES = {
    "DG_AI": {
        "ComfyUI": "https://github.com/comfyanonymous/ComfyUI",
        "OneTrainer": "https://github.com/Nerogar/OneTrainer",
        "Kohya_ss": "https://github.com/bmaltais/kohya_ss",
        "AI-Toolkit": "https://github.com/ostris/ai-toolkit"
    }
}

class AppManager:
    def __init__(self, root):
        self.apps_root = root
        self.uv = shutil.which("uv")

    def ensure_uv(self):
        if self.uv: return
        print("[INSTALL] Installing uv...")
        subprocess.run("curl -LsSf https://astral.sh/uv/install.sh | sh", shell=True, check=True)
        self.uv = shutil.which("uv")

    def clone_repo(self, repo_url, app_name):
        target = self.apps_root / app_name
        if target.exists():
            print(f"[UPDATE] git pull for {app_name}...")
            subprocess.run(["git", "pull"], cwd=target, check=False)
        else:
            print(f"[CLONE] {app_name}...")
            subprocess.run(["git", "clone", repo_url, str(target)], check=True)
        
        # FIX: Kohya requires submodules
        if app_name == "Kohya_ss":
            print("[SUBMODULE] Init for Kohya...")
            subprocess.run(["git", "submodule", "update", "--init", "--recursive"], cwd=target, check=False)
        return target

    def install_deps(self, target):
        print(f"[INSTALL] Dependencies for {target.name}...")
        
        # Strategy 1: Fast (UV)
        try:
            subprocess.run(["uv", "pip", "install", "-r", "requirements.txt"], cwd=target, check=True)
        except subprocess.CalledProcessError:
            print(f"[WARN] 'uv pip' failed. Attempting standard pip fallback...")
            # Strategy 2: Compat (Standard Pip via UV venv)
            subprocess.run(["uv", "pip", "install", "pip"], cwd=target, check=True)
            subprocess.run(["uv", "run", "pip", "install", "-r", "requirements.txt"], cwd=target, check=True)

    def scan_app(self, target):
        print("[SCAN] Generating manifest...")
        try:
            data = DG_dependency_scanner.scan_directory(target)
            with open(target / "manifest.json", "w") as f: json.dump(data, f, indent=2)
            print("[SUCCESS] Manifest saved.")
        except Exception as e:
            print(f"[WARN] Scanner skipped: {e}")

    def deploy(self, name, url):
        print(f"\n=== DEPLOYING: {name} ===")
        self.ensure_uv()
        target = self.clone_repo(url, name)
        
        print(f"[VENV] Creating venv for {name}...")
        subprocess.run(["uv", "venv", ".venv"], cwd=target, check=True)
        
        if (target / "requirements.txt").exists():
            self.install_deps(target)
        
        self.scan_app(target)
        print(f"[SUCCESS] {name} deployed.")

    def install_suite(self, suite):
        if suite not in DG_SUITES: return print(f"[ERROR] Unknown suite: {suite}")
        print(f"*** SUITE: {suite} ***")
        for name, url in DG_SUITES[suite].items():
            try: self.deploy(name, url)
            except Exception as e: print(f"[FAIL] {name}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3: sys.exit(1)
    # Fix path logic to ensure apps_managed is in correct spot
    root = Path(__file__).resolve().parent.parent / "apps_managed"
    root.mkdir(exist_ok=True)
    mgr = AppManager(root)
    
    if sys.argv[1] == "--suite": mgr.install_suite(sys.argv[2])
    else: mgr.deploy(sys.argv[1], sys.argv[2])
