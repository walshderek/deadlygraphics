import sys
import os
import base64
import utils
import re
from pathlib import Path

# --- CONFIGURATION ---
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434')
CAPTION_MODE = "fixed" # Default
FORBIDDEN_WORDS = ["hair", "eyes", "nose", "mouth", "skin", "makeup", "face"]

# Qwen Paths
QWEN_PATH = utils.BASE_PATH / "models" / "qwen-vl"

def strip_forbidden(text):
    """Post-process to remove sentences describing forbidden facial features."""
    sentences = text.split('.')
    clean = []
    for s in sentences:
        if not any(bad in s.lower() for bad in FORBIDDEN_WORDS):
            clean.append(s)
    return '.'.join(clean).strip()

def run(slug, model_type="moondream"):
    config = utils.load_config(slug)
    if not config: return
    trigger = config['trigger']
    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['crop']
    out_dir = path / utils.DIRS['caption']
    out_dir.mkdir(parents=True, exist_ok=True)

    files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    if not files: return
    
    print(f"📝 Captioning {len(files)} images using {model_type}...")

    # --- MODEL SETUP ---
    qwen_processor = None
    qwen_model = None
    ollama_client = None

    if model_type == "qwen-vl":
        from transformers import QwenVLProcessor, QwenVLChatModel
        import torch
        print("   Loading Qwen-VL (this takes memory)...")
        try:
            qwen_processor = QwenVLProcessor.from_pretrained(str(QWEN_PATH), trust_remote_code=True)
            qwen_model = QwenVLChatModel.from_pretrained(str(QWEN_PATH), device_map="cuda", trust_remote_code=True).eval()
        except Exception as e:
            print(f"❌ Failed to load Qwen-VL: {e}")
            return
    else:
        # Default Ollama
        import ollama
        ollama_client = ollama.Client(host=OLLAMA_HOST)

    count = 0
    for i, f in enumerate(files, 1):
        img_path = in_dir / f
        txt_path = out_dir / (os.path.splitext(f)[0] + ".txt")
        if txt_path.exists(): 
            count += 1
            continue

        print(f"   [{i}/{len(files)}] Processing {f}...", end="", flush=True)
        caption = ""

        # --- QWEN-VL LOGIC ---
        if model_type == "qwen-vl":
            query = qwen_processor.from_list_format([
                {'image': str(img_path)},
                {'text': f"Describe this image. Start with '{trigger}, '. Do not describe facial features."}
            ])
            inputs = qwen_processor(query, return_tensors='pt').to(qwen_model.device)
            gen_kwargs = {"max_new_tokens": 512, "do_sample": False}
            pred = qwen_model.generate(**inputs, **gen_kwargs)
            caption = qwen_processor.decode(pred[0], skip_special_tokens=False)
            # Cleanup Qwen output formatting
            caption = caption.split("Describe this image.")[-1].strip()

        # --- MOONDREAM LOGIC ---
        else:
            try:
                with open(img_path, "rb") as img_file:
                    b64 = base64.b64encode(img_file.read()).decode('utf-8')
                res = ollama_client.chat(model='moondream', messages=[{
                    'role': 'user', 
                    'content': f"Describe this image. Start with '{trigger}, '. RULES: Do NOT describe eyes/hair/face.", 
                    'images': [b64]
                }])
                caption = res['message']['content'].replace('\n', ' ').strip()
            except Exception as e:
                print(f" Err: {e}")

        # --- ENFORCEMENT ---
        # 1. Trigger
        if not caption.startswith(trigger):
            caption = f"{trigger}, {caption}"
        
        # 2. Forbidden Words (Fixed Mode)
        if CAPTION_MODE == "fixed":
            caption = strip_forbidden(caption)

        if not caption or len(caption) < 10:
            caption = f"{trigger}, a person."

        with open(txt_path, "w", encoding="utf-8") as tf: tf.write(caption)
        print(" Done.")
        count += 1

    print(f"✅ Captions complete.")

if __name__ == "__main__":
    run("test_slug")