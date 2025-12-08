import sys
import os
import base64
import time
import subprocess
import ollama
import utils

# Force localhost for WSL
OLLAMA_HOST = "http://127.0.0.1:11434"
os.environ["OLLAMA_HOST"] = OLLAMA_HOST
# Force Models Path (Critical for the server to find existing blobs)
os.environ["OLLAMA_MODELS"] = str(utils.MODEL_STORE_ROOT)

def ensure_ollama_server():
    """Checks if Ollama is running. If not, starts it with correct paths."""
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        client.list() # Ping
        return client
    except Exception:
        print(f"🔄 Ollama not running. Starting server using models at {utils.MODEL_STORE_ROOT}...")
        
        # Pass the environment variables explicitly
        env = os.environ.copy()
        env["OLLAMA_MODELS"] = str(utils.MODEL_STORE_ROOT)
        
        # Start in background
        subprocess.Popen(["ollama", "serve"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait loop
        for _ in range(30):
            try:
                client = ollama.Client(host=OLLAMA_HOST)
                client.list()
                print("✅ Ollama server started.")
                return client
            except:
                time.sleep(1)
        
        print("❌ Failed to start Ollama automatically.")
        sys.exit(1)

def ensure_model(client, model_name):
    """Checks if model exists. If not, pulls it."""
    try:
        list_response = client.list()
        # Handle different library versions
        if 'models' in list_response:
            existing_models = [m.get('name', '').split(':')[0] for m in list_response['models']]
        else:
            existing_models = []

        if model_name not in existing_models:
            print(f"⬇️ Model '{model_name}' missing from {utils.MODEL_STORE_ROOT}. Pulling now...")
            client.pull(model_name)
            print(f"✅ Model '{model_name}' installed.")
    except Exception as e:
        print(f"⚠️ Error checking models: {e}")

def generate_prompt(trigger, mode, gender_str="person"):
    # Ground the subject with gender
    subject_identity = f"{trigger}, a {gender_str}"
    
    if mode == "fixed":
        return (f"Describe this image of {subject_identity}.\n"
                f"Focus ONLY on clothing, background, pose, and lighting.\n"
                f"Do NOT describe facial features, eyes, hair, or makeup.\n"
                f"Keep the description concise and factual.")
    else:
        # Variable
        return (f"Describe this image of {subject_identity}.\n"
                f"Describe everything visible including hair, face, clothing, and background.\n"
                f"Keep the description concise.")

def run(slug, model="moondream", mode="fixed"):
    config = utils.load_config(slug)
    if not config: 
        print("❌ Config missing.")
        return
        
    trigger = config.get('trigger', slug[:4])
    # Map 'm'/'f' to full words for the prompt
    gender_map = {'m': 'man', 'f': 'woman'}
    gender_code = config.get('gender', 'm')
    gender_str = gender_map.get(gender_code, 'person')

    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['crop']
    out_dir = path / utils.DIRS['caption']
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. AUTO-START SERVER
    client = ensure_ollama_server()
    
    # 2. AUTO-PULL MODEL (Only for Ollama models)
    if model != "qwen-vl":
        ensure_model(client, model)

    files = [f for f in os.listdir(in_dir) if f.lower().endswith('.jpg')]
    print(f"📝 Captioning {len(files)} images with {model}...")

    # Load HF Qwen if needed
    qwen_processor, qwen_model_obj = None, None
    if model == "qwen-vl":
        from transformers import QwenVLProcessor, QwenVLForConditionalGeneration
        import torch
        # NEW: Point to the centralized C: drive location
        qwen_path = utils.MODEL_STORE_ROOT / "QWEN" / "qwen-vl"
        
        if not qwen_path.exists():
            print(f"❌ Qwen model not found at {qwen_path}. Run utils.bootstrap() first.")
            return

        print(f"⏳ Loading Qwen-VL from {qwen_path}...")
        try:
            qwen_processor = QwenVLProcessor.from_pretrained(str(qwen_path), trust_remote_code=True)
            qwen_model_obj = QwenVLForConditionalGeneration.from_pretrained(
                str(qwen_path), device_map="auto", trust_remote_code=True
            ).eval()
        except Exception as e:
            print(f"❌ Failed to load Qwen: {e}")
            return

    for i, f in enumerate(files, 1):
        txt_path = out_dir / (os.path.splitext(f)[0] + ".txt")
        if txt_path.exists(): continue
            
        img_path = in_dir / f
        caption = ""
        final_prompt = generate_prompt(trigger, mode, gender_str)
        
        # --- GENERATE ---
        if model == "qwen-vl":
            try:
                inputs = qwen_processor.apply_chat_template(
                    [{"role": "user", "content": final_prompt, "image": str(img_path)}],
                    return_tensors="pt"
                )
                inputs = inputs.to(qwen_model_obj.device)
                outputs = qwen_model_obj.generate(**inputs, max_new_tokens=256)
                caption = qwen_processor.decode(outputs[0], skip_special_tokens=True)
                if "concise and factual." in caption:
                    caption = caption.split("concise and factual.")[-1].strip()
            except Exception as e:
                print(f"    ⚠️ Qwen Error: {e}")
                caption = f"{trigger}, a {gender_str}."
        else:
            # MOONDREAM / OLLAMA
            try:
                with open(img_path, "rb") as ifile:
                    b64 = base64.b64encode(ifile.read()).decode('utf-8')
                
                # Robust API call
                res = client.chat(
                    model=model,
                    messages=[{'role': 'user', 'content': final_prompt, 'images': [b64]}],
                    options={'timeout': 120} 
                )
                caption = res['message']['content'].replace('\n', ' ').strip()
            except Exception as e:
                print(f"    ⚠️ Caption failed for {f}: {e}")
                caption = f"{trigger}, a {gender_str}."

        # Enforcement
        caption = caption.strip('"').strip("'")
        if not caption.lower().startswith(trigger.lower()):
            caption = f"{trigger}, {caption}"
            
        with open(txt_path, "w", encoding="utf-8") as tf:
            tf.write(caption)
        
        print(f"   [{i}/{len(files)}] Done: {caption[:50]}...")

    print(f"✅ Captions complete.")