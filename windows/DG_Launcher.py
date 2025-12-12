# File: wsl/DG_Launcher.py
#!/usr/bin/env python3
"""
Deadly Graphics — WSL Image Launcher (GPU-strict, resumable)

Goals (BOOTSTRAP PHASE):
- Each app has its own venv
- Never uses system Python for app runtime
- Never shares Torch binaries between apps
- HARD GPU requirement (Torch must see CUDA) — fail fast if not
- --resume continues from last successful step using ~/.dg_state.json
- apps live under repo/wsl/apps_managed but are git-ignored (no embedded repo disasters)
- full clarity: logs + per-venv pip freeze captured to ~/.dg_logs/
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


# ============================================================
# CONFIG
# ============================================================

STATE_FILE = Path.home() / ".dg_state.json"
LOGS_DIR = Path.home() / ".dg_logs"

REPO_ROOT = Path.home() / "workspace" / "deadlygraphics"
WSL_DIR = REPO_ROOT / "wsl"
APPS_ROOT = WSL_DIR / "apps_managed"          # ephemeral installs (gitignored)
CACHE_DIR = Path.home() / ".cache" / "dg"     # future use

UV_INSTALL_CMD = "curl -LsSf https://astral.sh/uv/install.sh | sh"
UV_ENV_SH = Path.home() / ".local" / "bin" / "env"  # created by uv installer
LOCAL_BIN = Path.home() / ".local" / "bin"

# GPU / CUDA
CUDA_APT_KEYRING = "/etc/apt/keyrings/cuda-archive-keyring.gpg"
CUDA_APT_LIST = "/etc/apt/sources.list.d/cuda-wsl.list"
CUDA_TOOLKIT_PKG = "cuda-toolkit-12-4"

# Torch CUDA wheel index (adjust later if you standardise on another CUDA)
TORCH_INDEX_URL = "https://download.pytorch.org/whl/cu124"

# Apps (bootstrap set)
DG_APPS: Dict[str, Dict[str, str]] = {
    "ComfyUI": {
        "repo": "https://github.com/comfyanonymous/ComfyUI.git",
        "dir": str(APPS_ROOT / "ComfyUI"),
        "requirements": "requirements.txt",
    },
    "OneTrainer": {
        "repo": "https://github.com/Nerogar/OneTrainer.git",
        "dir": str(APPS_ROOT / "OneTrainer"),
        # OneTrainer install varies; we'll prefer requirements if present, else fallback to editable install.
        "requirements": "requirements.txt",
    },
    "AI-Toolkit": {
        "repo": "https://github.com/ostris/ai-toolkit.git",
        "dir": str(APPS_ROOT / "AI-Toolkit"),
        "requirements": "requirements.txt",
    },
    "Kohya_ss": {
        "repo": "https://github.com/bmaltais/kohya_ss.git",
        "dir": str(APPS_ROOT / "Kohya_ss"),
        "requirements": "requirements.txt",
    },
}


# ============================================================
# STATE
# ============================================================

class StateManager:
    def __init__(self, filename: Path):
        self.filename = filename
        self.state = self._load()

    def _load(self) -> dict:
        if self.filename.exists():
            try:
                return json.loads(self.filename.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def save(self) -> None:
        self.filename.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def is_done(self, step_name: str) -> bool:
        return self.state.get(step_name, {}).get("status") == "success"

    def mark_success(self, step_name: str) -> None:
        self.state[step_name] = {"status": "success", "ts": time.time()}
        self.save()

    def mark_failed(self, step_name: str, error: Exception) -> None:
        self.state[step_name] = {"status": "failed", "error": str(error), "ts": time.time()}
        self.save()


# ============================================================
# EXEC / LOGGING
# ============================================================

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def now_tag() -> str:
    return time.strftime("%Y%m%d_%H%M%S")

def env_with_local_bin() -> dict:
    env = os.environ.copy()
    env["PATH"] = f"{LOCAL_BIN}:{env.get('PATH','')}"
    return env

def run(cmd: str, *, cwd: Optional[Path] = None) -> None:
    """
    Stream output to console, and tee into a per-run log file.
    """
    ensure_dir(LOGS_DIR)
    log_file = LOGS_DIR / f"dg_launcher_{now_tag()}.log"

    print(f"\n💎 EXEC: {cmd}")
    if cwd:
        print(f"   cwd: {cwd}")

    # tee-like logging
    with log_file.open("a", encoding="utf-8") as lf:
        lf.write(f"\n=== {time.ctime()} ===\n$ {cmd}\n")
        lf.flush()

        p = subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd else None,
            shell=True,
            env=env_with_local_bin(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert p.stdout is not None
        for line in p.stdout:
            print(line, end="")
            lf.write(line)
        rc = p.wait()
        if rc != 0:
            raise subprocess.CalledProcessError(rc, cmd)

def which_or_fail(name: str) -> str:
    p = shutil.which(name, path=env_with_local_bin().get("PATH"))
    if not p:
        raise RuntimeError(f"Required tool not found on PATH: {name}")
    return p


# ============================================================
# TELEMETRY
# ============================================================

def write_json(name: str, data: dict) -> None:
    ensure_dir(LOGS_DIR)
    (LOGS_DIR / name).write_text(json.dumps(data, indent=2), encoding="utf-8")

def collect_host_telemetry() -> None:
    # Minimal WSL-side telemetry (Windows-side system_specs.ps1 remains authoritative)
    data = {
        "ts": time.time(),
        "platform": platform.platform(),
        "python": sys.version,
        "uname": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
    }
    # Optional: nvidia-smi if present
    try:
        out = subprocess.check_output("nvidia-smi -L", shell=True, text=True, env=env_with_local_bin())
        data["nvidia_smi_L"] = out.strip()
    except Exception:
        data["nvidia_smi_L"] = None
    write_json(f"wsl_telemetry_{now_tag()}.json", data)


def pip_freeze(venv_dir: Path, out_name: str) -> None:
    py = venv_dir / "bin" / "python"
    if not py.exists():
        return
    try:
        out = subprocess.check_output(
            f"{py} -m pip freeze",
            shell=True,
            text=True,
            env=env_with_local_bin(),
        )
        (LOGS_DIR / out_name).write_text(out, encoding="utf-8")
    except Exception:
        pass


# ============================================================
# GPU HARD ASSERTS
# ============================================================

def verify_wsl_gpu_visible() -> None:
    """
    HARD infrastructure check: if GPU passthrough is broken, stop here.
    """
    # nvidia-smi is the quickest sanity check in WSL when NVIDIA drivers are installed on Windows
    run("command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi || (echo '❌ nvidia-smi missing or failing' && exit 1)")

def install_torch_cuda_strict(venv_dir: Path) -> None:
    """
    Install CUDA-enabled torch into THIS venv only, then hard-assert CUDA availability.
    """
    pip_bin = venv_dir / "bin" / "pip"
    py_bin = venv_dir / "bin" / "python"
    if not pip_bin.exists() or not py_bin.exists():
        raise RuntimeError(f"Venv incomplete: {venv_dir}")

    run(f"{pip_bin} install --upgrade pip setuptools wheel")

    # Torch per-venv, never shared.
    run(
        f"{pip_bin} install torch torchvision torchaudio "
        f"--index-url {TORCH_INDEX_URL}"
    )

    # HARD ASSERT: torch.cuda.is_available must be True
    run(
        f"""{py_bin} - << 'EOF'
import sys
import torch
print("Torch:", torch.__version__)
print("Torch CUDA build:", torch.version.cuda)
print("CUDA available:", torch.cuda.is_available())
if not torch.cuda.is_available():
    print("❌ CUDA NOT AVAILABLE — ABORTING")
    sys.exit(1)
print("✅ CUDA OK")
EOF"""
    )


# ============================================================
# GIT HYGIENE (NO SUBMODULE DISASTERS)
# ============================================================

def ensure_gitignore_ephemeral_apps() -> None:
    ensure_dir(APPS_ROOT)
    gi = WSL_DIR / ".gitignore"
    entry = "apps_managed/"
    existing = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if entry not in existing:
        gi.write_text(existing + ("\n" if existing and not existing.endswith("\n") else "") + entry + "\n", encoding="utf-8")
        print(f"✅ Added '{entry}' to {gi}")


# ============================================================
# INSTALL HELPERS
# ============================================================

def repo_pull() -> None:
    if REPO_ROOT.exists():
        run("git pull", cwd=REPO_ROOT)

def apt_base_deps() -> None:
    run("sudo apt-get update")
    run("sudo apt-get install -y python3 python3-venv python3-pip git curl ca-certificates gnupg lsb-release wget build-essential libgl1 libglib2.0-0")

def install_cuda_toolkit_wsl() -> None:
    """
    CUDA toolkit installation (WSL Ubuntu repo). You requested GPU CUDA explicitly at infra level.
    """
    run("sudo apt-get update")
    run("sudo mkdir -p /etc/apt/keyrings")

    # key + repo
    run(
        f"curl -fsSL https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/3bf863cc.pub | "
        f"sudo gpg --dearmor -o {CUDA_APT_KEYRING} --yes"
    )
    run(
        f'echo "deb [signed-by={CUDA_APT_KEYRING}] https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/ /" | '
        f"sudo tee {CUDA_APT_LIST}"
    )
    run("sudo apt-get update")
    run(f"sudo apt-get install -y {CUDA_TOOLKIT_PKG}")

def install_uv() -> None:
    # installs to ~/.local/bin by default
    run(UV_INSTALL_CMD)
    # uv installer prints instructions to source env; we don’t rely on shell state, we enforce PATH in env_with_local_bin.
    which_or_fail("uv")

def clone_or_pull(app_name: str, repo_url: str, target_dir: Path) -> None:
    if target_dir.exists() and (target_dir / ".git").exists():
        run("git pull", cwd=target_dir)
        return
    if target_dir.exists():
        # directory exists but not a git repo — treat as partial/broken, do not delete automatically
        raise RuntimeError(f"{app_name} target dir exists but is not a git repo: {target_dir}")
    ensure_dir(target_dir.parent)
    run(f"git clone {repo_url} {target_dir}")

def ensure_venv(app_dir: Path) -> Path:
    venv_dir = app_dir / ".venv"
    if venv_dir.exists() and (venv_dir / "bin" / "python").exists():
        return venv_dir
    run("python3 -m venv .venv", cwd=app_dir)
    return venv_dir

def pip_install_requirements(app_dir: Path, venv_dir: Path, req_rel: str) -> None:
    req = app_dir / req_rel
    if not req.exists():
        print(f"[WARN] No {req_rel} found for {app_dir.name} — skipping requirements install.")
        return
    pip_bin = venv_dir / "bin" / "pip"
    run(f"{pip_bin} install -r {req.name}", cwd=app_dir)

def pip_install_editable_if_pyproject(app_dir: Path, venv_dir: Path) -> None:
    pyproject = app_dir / "pyproject.toml"
    if not pyproject.exists():
        return
    pip_bin = venv_dir / "bin" / "pip"
    run(f"{pip_bin} install -e .", cwd=app_dir)


# ============================================================
# STEPS (RESUMABLE)
# ============================================================

@dataclass
class Step:
    name: str
    fn: Callable[[], None]

def step_00_telemetry() -> None:
    collect_host_telemetry()

def step_01_repo_pull() -> None:
    repo_pull()

def step_02_base_deps() -> None:
    apt_base_deps()

def step_03_cuda_toolkit() -> None:
    install_cuda_toolkit_wsl()

def step_04_verify_gpu_passthrough() -> None:
    verify_wsl_gpu_visible()

def step_05_uv() -> None:
    install_uv()

def step_06_git_hygiene() -> None:
    ensure_gitignore_ephemeral_apps()

def make_app_steps() -> List[Step]:
    steps: List[Step] = []

    for app_name, meta in DG_APPS.items():
        repo = meta["repo"]
        app_dir = Path(meta["dir"])
        req = meta.get("requirements", "requirements.txt")

        def _make_install(app_name=app_name, repo=repo, app_dir=app_dir, req=req) -> Callable[[], None]:
            def _fn() -> None:
                print(f"\n=== APP INSTALL: {app_name} ===")
                clone_or_pull(app_name, repo, app_dir)

                venv_dir = ensure_venv(app_dir)

                # HARD: per-app Torch GPU install + assert (never shared)
                install_torch_cuda_strict(venv_dir)

                # App-specific deps (as per their repos)
                pip_install_requirements(app_dir, venv_dir, req)
                pip_install_editable_if_pyproject(app_dir, venv_dir)

                # capture freeze for later convergence analysis
                pip_freeze(venv_dir, f"{app_name}_pip_freeze_{now_tag()}.txt")

            return _fn

        steps.append(Step(name=f"app_install::{app_name}", fn=_make_install()))

    return steps


BASE_STEPS: List[Step] = [
    Step("telemetry", step_00_telemetry),
    Step("repo_pull", step_01_repo_pull),
    Step("base_deps", step_02_base_deps),
    Step("cuda_toolkit", step_03_cuda_toolkit),
    Step("verify_gpu", step_04_verify_gpu_passthrough),
    Step("uv", step_05_uv),
    Step("git_hygiene", step_06_git_hygiene),
]


# ============================================================
# MAIN
# ============================================================

def run_sequence(resume: bool) -> None:
    mgr = StateManager(STATE_FILE)
    steps = BASE_STEPS + make_app_steps()

    print(f"\n💎 DG_Launcher (WSL) | resume={resume}")
    print(f"Repo: {REPO_ROOT}")
    print(f"Apps: {APPS_ROOT}")
    print(f"State: {STATE_FILE}")
    print(f"Logs: {LOGS_DIR}\n")

    # sanity: must run inside WSL with repo present
    if not REPO_ROOT.exists():
        raise RuntimeError(f"Repo root not found at {REPO_ROOT}. (smash_diamond.ps1 should have cloned it)")

    for s in steps:
        if mgr.is_done(s.name):
            print(f"✅ Skipping {s.name} (done)")
            continue

        print(f"\n🚀 STEP: {s.name}")
        try:
            s.fn()
            mgr.mark_success(s.name)
            print(f"✨ OK: {s.name}")
        except Exception as e:
            mgr.mark_failed(s.name, e)
            print(f"\n💥 FAIL: {s.name}\n   {e}")
            print("\nNext action:")
            print(f"- Fix the issue, then rerun with --resume")
            print(f"- State file: {STATE_FILE}")
            sys.exit(1)

    print("\n✅ ALL STEPS COMPLETE")
    print("Next:")
    print("- Use your Windows-side launcher to start apps (or add app start commands later).")
    print("- Phase 4: compare pip_freeze outputs for convergence candidates.")


def show_status() -> None:
    mgr = StateManager(STATE_FILE)
    print(json.dumps(mgr.state, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true", help="Run full build sequence")
    parser.add_argument("--resume", action="store_true", help="Resume from last successful step")
    parser.add_argument("--status", action="store_true", help="Show state file")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.install or args.resume:
        run_sequence(resume=args.resume)
        return

    print("Usage: python3 wsl/DG_Launcher.py --install | --resume | --status")


if __name__ == "__main__":
    main()
