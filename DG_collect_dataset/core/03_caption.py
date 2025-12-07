import sys
import os
import time
import subprocess
import requests
import base64
import tarfile
import io
import shutil
import utils

# --- CONFIGURATION ---
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434')
CAPTION_MODE = "fixed"
MODEL_NAME = "moondream"

# Path to install/find the Ollama Binary
OLLAMA_APP_DIR = utils.BASE_PATH.parent / "ollama"
OLLAMA_BIN = OLLAMA_APP_DIR / "ollama"
LOG_FILE = OLLAMA_APP_DIR / "ollama_server.log"

try:
    import ollama
    client = ollama.Client(host=OLLAMA_HOST)
except ImportError:
    print("⚠️ Ollama library not found. Run: pip install ollama")
    client = None

def check_gpu_wsl():
    """Checks if NVIDIA GPU is visible in WSL."""
    try:
        # Run nvidia-smi to see if drivers are passed through
        result = subprocess.run(['nvidia-smi', '-L'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            print(f"✅ GPU Detected: {result.stdout.strip()}")
            return True
        else:
            print("⚠️  WARNING: nvidia-smi failed. Ollama will likely run on SLOW CPU.")
            print("   Fix: Run 'bash install_cuda_wsl.sh' in your project root.")
            return False
    except FileNotFoundError:
        print("⚠️  WARNING: nvidia-smi not found. Run 'bash install_cuda_wsl.sh'.")
        return False

def kill_stale_ollama():
    """Kills existing ollama processes to ensure clean GPU binding."""
    try:
        subprocess.run(['pkill', '-f', 'ollama serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1) 
    except Exception:
        pass

def install_ollama_binary():
    """Downloads the Ollama Linux binary (TGZ) and extracts it."""
    print(f"📦 Ollama binary not found. Installing to {OLLAMA_APP_DIR}...")
    OLLAMA_APP_DIR.mkdir(parents=True, exist_ok=True)
    
    url = "https://ollama.com/download/ollama-linux-amd64.tgz"
    
    try:
        print(f"   Downloading from {url}...")
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            print(f"❌ Failed to download. Status: {response.status_code}")
            return False
            
        with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as tar:
            member = next((m for m in tar.getmembers() if m.name.endswith("ollama")), None)
            if not member:
                print("❌ 'ollama' binary not found inside archive.")
                return False
            f = tar.extractfile(member)
            with open(OLLAMA_BIN, 'wb') as out:
                out.write(f.read())
        
        os.chmod(OLLAMA_BIN, 0o755)
        print("✅ Ollama binary installed.")
        return True
    except Exception as e:
        print(f"❌ Failed to download/install Ollama: {e}")
        return False

def is_server_running():
    try:
        requests.get(OLLAMA_HOST, timeout=0.5)
        return True
    except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
        return False

def start_ollama_server():
    # 1. Check GPU first
    if not check_gpu_wsl():
        print("   (Proceeding anyway, but performance will be degraded)")
    
    # 2. Kill old processes
    kill_stale_ollama()

    print(f"🔄 Starting Ollama server (Logs: {LOG_FILE})...")
    
    # 3. Prepare Environment
    env = os.environ.copy()
    env['OLLAMA_MODELS'] = utils.OLLAMA_MODELS_WSL
    env['OLLAMA_HOST'] = "0.0.0.0:11434"
    
    # --- GPU ENFORCEMENT ---
    env['CUDA_VISIBLE_DEVICES'] = "0" 
    env['OLLAMA_NUM_GPU'] = "999" # Force offload all layers to GPU
    
    log_f = open(LOG_FILE, "w")
    try:
        subprocess.Popen(
            [str(OLLAMA_BIN), "serve"], 
            env=env,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
    except Exception as e:
        print(f"❌ Failed to launch subprocess: {e}")
        return False
    
    # 4. Wait for startup
    print("   Waiting for Ollama API...", end="", flush=True)
    retries = 0
    while retries < 30: 
        if is_server_running():
            print(" Online.")
            return True
        time.sleep(1)
        if retries % 5 == 0: print(".", end="", flush=True)
        retries += 1
    
    print("\n❌ Failed to start Ollama server. Check logs.")
    return False

def ensure_model(model_name):
    if not is_server_running(): return False
    try:
        try:
            models = client.list()
            model_list = models.get('models', [])
            found = any(m['name'].startswith(model_name) for m in model_list)
        except Exception:
            found = False
        
        if not found:
            print(f"⬇️  Pulling model '{model_name}' (This may take a moment)...")
            client.pull(model_name)
            print(f"✅ Model '{model_name}' ready.")
        return True
    except Exception as e:
        print(f"❌ Error checking models: {e}")
        return False

def bootstrap_ollama():
    if not OLLAMA_BIN.exists():
        if not install_ollama_binary(): return False
    
    # Always restart server to ensure we grab the GPU
    if not start_ollama_server(): return False
    
    if not ensure_model(MODEL_NAME): return False
    return True

def generate_prompt(trigger, mode):
    base_instr = f"The person in this image is named {trigger}. "
    if mode == "fixed":
        return (f"{base_instr}\nDescribe the image for an AI training dataset.\n"
                f"RULES:\n1. Start the sentence exactly with '{trigger}, '.\n"
                f"2. Describe CLOTHING, BACKGROUND, POSE, LIGHTING.\n"
                f"3. Do NOT describe facial features, makeup, or hairstyle.\n"
                f"4. Keep it to one concise paragraph.")
    else:
        return (f"{base_instr}\nDescribe the image for an AI training dataset.\n"
                f"RULES:\n1. Start the sentence exactly with '{trigger}, '.\n"
                f"2. Describe CLOTHING, BACKGROUND, POSE, LIGHTING.\n"
                f"3. Describe HAIRSTYLE and FACIAL HAIR explicitly.\n"
                f"4. Do NOT describe underlying facial structure.\n"
                f"5. Keep it to one concise paragraph.")

def run(project_slug):
    # 0. BOOTSTRAP OLLAMA
    if not bootstrap_ollama():
        print("❌ Ollama setup failed. Cannot caption.")
        return

    config = utils.load_config(project_slug)
    if not config: return
    
    trigger = config['trigger']
    path = utils.get_project_path(project_slug)
    in_dir = path / utils.DIRS['crop']
    out_dir = path / utils.DIRS['caption']
    
    if not in_dir.exists(): return
    files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    if not files: return

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"📝 Captioning {len(files)} images for {trigger} (Mode: {CAPTION_MODE})...")
    
    count = 0
    # Process Loop
    for i, f in enumerate(files, 1):
        img_path = in_dir / f
        txt_path = out_dir / (os.path.splitext(f)[0] + ".txt")
        
        if txt_path.exists():
            count += 1
            print(f"   [{i}/{len(files)}] {f} already exists.")
            continue
        
        # Real-time feedback
        print(f"   [{i}/{len(files)}] Processing {f}...", end="", flush=True)
        
        caption = ""
        if client:
            try:
                with open(img_path, "rb") as img_file:
                    b64_data = base64.b64encode(img_file.read()).decode('utf-8')
                
                final_prompt = generate_prompt(trigger, CAPTION_MODE)
                
                # The API Call
                res = client.chat(
                    model=MODEL_NAME, 
                    messages=[{'role': 'user', 'content': final_prompt, 'images': [b64_data]}]
                )
                
                caption = res['message']['content'].replace('\n', ' ').strip()
                
                if not caption.startswith(trigger):
                    caption = f"{trigger}, {caption}"
                
                print(f" Done.") 
                
            except Exception as e:
                print(f"\n   ⚠️ Error on {f}: {e}")
        
        if not caption:
            caption = f"{trigger}, a person."

        with open(txt_path, "w", encoding="utf-8") as tf:
            tf.write(caption)
        
        count += 1

    print(f"✅ Generated {count} captions.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])