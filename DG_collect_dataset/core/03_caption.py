import sys
import os
import base64
import time
import subprocess
import ollama
import utils
import re

# Force localhost for WSL
OLLAMA_HOST = "http://127.0.0.1:11434"
os.environ["OLLAMA_HOST"] = OLLAMA_HOST
os.environ["OLLAMA_MODELS"] = str(utils.MODEL_STORE_ROOT)

def ensure_ollama_server():
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        client.list() 
        return client
    except Exception:
        print("🔄 Ollama not running. Starting server...")
        env = os.environ.copy()
        env["OLLAMA_MODELS"] = str(utils.MODEL_STORE_ROOT)
        subprocess.Popen(["ollama", "serve"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(30):
            try:
                client = ollama.Client(host=OLLAMA_HOST)
                client.list()
                print("✅ Ollama server started.")
                return client
            except: time.sleep(1)
        print("❌ Failed to start Ollama automatically.")
        sys.exit(1)

def ensure_model(client, model_name):
    try:
        list_response = client.list()
        if 'models' in list_response:
            existing = [m.get('name', '').split(':')[0] for m in list_response['models']]
        else: existing = []
        if model_name not in existing:
            print(f"⬇️ Model '{model_name}' missing. Pulling...")
            client.pull(model_name)
    except: pass

def generate_prompt(trigger, mode, gender_str="person"):
    if mode == "fixed":
        return (f"Photo of {trigger}, a {gender_str}.\n"
                f"RULES:\n"
                f"1. Describe CLOTHING, BACKGROUND, POSE, and LIGHTING.\n"
                f"2. Do NOT describe facial features, makeup, or hairstyle.\n"
                f"3. Keep it to one concise paragraph.")
    return f"Photo of {trigger}, a {gender_str}. Describe everything visible."

def clean_caption(text, trigger):
    """Aggressive regex cleaning."""
    clean = text.strip()
    
    # Remove "An AI...", "The image shows...", etc case-insensitive
    clean = re.sub(r"(?i)^(an ai training dataset (image )?shows|the image shows|the image features|in this image,|a photo of|describe the image:)\s*", "", clean)
    
    clean = clean.lstrip(",. :")
    
    # Fix: Ensure we don't double up ("ohwx, ohwx")
    trigger_lower = trigger.lower()
    clean_lower = clean.lower()
    
    if not clean_lower.startswith(trigger_lower):
        clean = f"{trigger}, {clean}"
    
    # Final fallback if empty
    if len(clean) < len(trigger) + 5:
        clean = f"{trigger}, a person."
        
    return clean

def run(slug, model="moondream", mode="fixed"):
    config = utils.load_config(slug)
    if not config: return
    trigger = config['trigger']
    gender_map = {'m': 'man', 'f': 'woman'}
    gender_str = gender_map.get(config.get('gender', 'm'), 'person')

    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['crop']
    out_dir = path / utils.DIRS['caption']
    out_dir.mkdir(parents=True, exist_ok=True)

    client = ensure_ollama_server()
    if model != "qwen-vl": ensure_model(client, model)

    files = [f for f in os.listdir(in_dir) if f.lower().endswith('.jpg')]
    print(f"📝 Captioning {len(files)} images with {model}...")

    # Qwen Setup
    qwen_processor, qwen_model_obj = None, None
    if model == "qwen-vl":
        from transformers import QwenVLProcessor, QwenVLForConditionalGeneration
        import torch
        qwen_path = utils.MODEL_STORE_ROOT / "QWEN" / "qwen-vl"
        qwen_processor = QwenVLProcessor.from_pretrained(str(qwen_path), trust_remote_code=True)
        qwen_model_obj = QwenVLForConditionalGeneration.from_pretrained(
            str(qwen_path), device_map="auto", trust_remote_code=True
        ).eval()

    for i, f in enumerate(files, 1):
        txt_path = out_dir / (os.path.splitext(f)[0] + ".txt")
        if txt_path.exists(): continue
            
        img_path = in_dir / f
        caption = ""
        prompt = generate_prompt(trigger, mode, gender_str)
        
        print(f"   [{i}/{len(files)}] Processing {f}...", end="", flush=True)

        try:
            if model == "qwen-vl":
                inputs = qwen_processor.apply_chat_template(
                    [{"role": "user", "content": prompt, "image": str(img_path)}],
                    return_tensors="pt"
                )
                inputs = inputs.to(qwen_model_obj.device)
                outputs = qwen_model_obj.generate(**inputs, max_new_tokens=256)
                caption = qwen_processor.decode(outputs[0], skip_special_tokens=True)
                if "concise paragraph." in caption:
                    caption = caption.split("concise paragraph.")[-1].strip()
            else:
                with open(img_path, "rb") as ifile:
                    b64 = base64.b64encode(ifile.read()).decode('utf-8')
                
                res = client.chat(
                    model='moondream', 
                    messages=[{'role': 'user', 'content': prompt, 'images': [b64]}],
                    options={'timeout': 60} 
                )
                caption = res['message']['content'].replace('\n', ' ').strip()
        except Exception as e:
            print(f" ⚠️ Fail: {e}")
            caption = f"{trigger}, a {gender_str}."

        caption = clean_caption(caption, trigger)
        
        with open(txt_path, "w", encoding="utf-8") as tf:
            tf.write(caption)
        
        print(f" Done.")

    print(f"✅ Captions complete.")