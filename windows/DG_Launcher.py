#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# --- CONFIGURATION ---
WORKSPACE_DIR = Path.home() / "workspace" / "deadlygraphics"
APPS_DIR = WORKSPACE_DIR / "ai" / "apps"
LOG_DIR = Path.home() / ".dg_logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / f"dg_launcher_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# --- LOCKED VERSIONS (FROM TSV) ---
TORCH_CMD = (
    "torch==2.5.1+cu124 "
    "torchvision==0.20.1+cu124 "
    "torchaudio==2.5.1+cu124"
)
TORCH_INDEX = "--index-url https://download.pytorch.org/whl/cu124"

APPS = {
    "ComfyUI": {
        "repo": "https://github.com/comfyanonymous/ComfyUI.git",
        "path": "ComfyUI",
        "requirements": "requirements.txt"
    },
    "OneTrainer": {
        "repo": "https://github.com/Nerogar/OneTrainer.git",
        "path": "OneTrainer",
        "requirements": "requirements.txt"
    },
    "AI-Toolkit": {
        "repo": "https://github.com/ostris/ai-toolkit.git",
        "path": "AI-Toolkit",
        "requirements": "requirements.txt"
    },
    "DG_collect_dataset": {
        "repo": "https://github.com/walshderek/deadlygraphics.git",
        "path": "DG_collect_dataset",
        "requirements": "ai/apps/DG_collect_dataset/requirements.txt"
    },
    "DG_videoscraper": {
        "repo": "https://github.com/walshderek/deadlygraphics.git",
        "path": "DG_videoscraper",
        "requirements": "ai/apps/DG_videoscraper/requirements.txt"
    }
}

# ---------------- UTIL ----------------

def log(msg):
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")

def run(cmd, cwd=None):
    log(f"💎 EXEC: {cmd}")
    subprocess.run(cmd, shell=True, check=True, cwd=cwd)

# ---------------- GUARDS ----------------

def assert_cuda_present():
    try:
        subprocess.run(["nvidia-smi"], check=True, stdout=subprocess.DEVNULL)
        log("✅ NVIDIA driver detected")
    except Exception:
        log("❌ NVIDIA driver / CUDA not available. Provisioning is broken.")
        sys.exit(1)

def assert_python():
    log(f"🐍 Python: {sys.version.split()[0]} ({sys.executable})")

# ---------------- VENV ----------------

def ensure_venv(app_path: Path):
    venv_path = app_path / ".venv"
    if not venv_path.exists():
        log(f"🛠️ Creating venv: {venv_path}")
        run(f"python3 -m venv {venv_path}")
    return venv_path

# ---------------- INSTALL ----------------

def install_app(name, config):
    app_path = APPS_DIR / config["path"]

    # Clone
    if not app_path.exists():
        log(f"⬇️ Cloning {name}")
        run(f"git clone {config['repo']} {app_path}")

    # Venv
    venv = ensure_venv(app_path)
    pip = venv / "bin" / "pip"
    python = venv / "bin" / "python"

    # Pip upgrade
    run(f"{pip} install --upgrade pip wheel")

    # Torch (STRICT, GPU)
    log(f"🔥 Installing Torch (cu124) for {name}")
    run(f"{pip} install {TORCH_CMD} {TORCH_INDEX}")

    # GPU assert
    run(
        f"""{python} - << 'EOF'
import torch, sys
assert torch.cuda.is_available(), "CUDA NOT AVAILABLE"
print("✅ GPU OK:", torch.cuda.get_device_name(0))
print("Torch:", torch.__version__)
print("CUDA:", torch.version.cuda)
EOF"""
    )

    # Requirements
    req = app_path / config["requirements"]
    if not req.exists():
        req = WORKSPACE_DIR / config["requirements"]

    if req.exists():
        log(f"📦 Installing requirements for {name}")
        run(f"{pip} install -r {req}", cwd=app_path)
    else:
        log(f"⚠️ No requirements.txt for {name}")

# ---------------- MAIN ----------------

def main():
    if "--install" not in sys.argv:
        log("Usage: python3 DG_Launcher.py --install")
        sys.exit(1)

    assert_python()
    assert_cuda_present()

    APPS_DIR.mkdir(parents=True, exist_ok=True)

    for name, config in APPS.items():
        log(f"\n=== {name} ===")
        install_app(name, config)

    log("\n💎 DIAMOND SMASHING COMPLETE 💎")
    log(f"📄 Log written to: {LOG_FILE}")

if __name__ == "__main__":
    main()
