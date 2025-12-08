import sys
import os
import base64
import ollama
import utils
import re

OLLAMA_HOST = "http://127.0.0.1:11434"
os.environ["OLLAMA_HOST"] = OLLAMA_HOST
os.environ["OLLAMA_MODELS"] = str(utils.MODEL_STORE_ROOT)

def ensure_ollama_server():
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        client.list() 
        return client
    except Exception: return None # Assume user has it running or we fail

def generate_prompt(trigger, mode, gender_str="person"):
    base = f"Photo of the face of {trigger}, a {gender_str}. "
    if mode == "fixed":
        return (f"{base}\nRULES:\n1. Describe CLOTHING, BACKGROUND, POSE.\n2. Do NOT describe face.\n3. Concise.")
    return base + " Describe everything."

def clean_caption(text, trigger):
    clean = text.strip()
    clean = re.sub(r"(?i)^(an ai training dataset (image )?shows|the image shows|this is an image of|describe the image:)\s*", "", clean)
    clean = clean.lstrip(",. :")
    if not clean.lower().startswith(trigger.lower()):
        clean = f"{trigger}, {clean}"
    return clean

def run(slug, model="moondream", mode="fixed"):
    config = utils.load_config(slug)
    if not config: return
    trigger = config['trigger']
    gender_str = {'m': 'man', 'f': 'woman'}.get(config.get('gender', 'm'), 'person')

    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['crop']
    out_dir = path / utils.DIRS['caption']
    out_dir.mkdir(parents=True, exist_ok=True)

    client = ensure_ollama_server()
    if not client and model != "qwen-vl": 
        print("❌ Ollama not found."); return

    files = [f for f in os.listdir(in_dir) if f.lower().endswith('.jpg')]
    print(f"📝 Captioning {len(files)} images...")

    qwen_processor, qwen_model_obj = None, None
    if model == "qwen-vl":
        from transformers import QwenVLProcessor, QwenVLForConditionalGeneration
        qwen_path = utils.MODEL_STORE_ROOT / "QWEN" / "qwen-vl"
        qwen_processor = QwenVLProcessor.from_pretrained(str(qwen_path), trust_remote_code=True)
        qwen_model_obj = QwenVLForConditionalGeneration.from_pretrained(str(qwen_path), device_map="auto", trust_remote_code=True).eval()

    for i, f in enumerate(files, 1):
        txt_path = out_dir / (os.path.splitext(f)[0] + ".txt")
        if txt_path.exists(): continue
        
        img_path = in_dir / f
        caption = ""
        prompt = generate_prompt(trigger, mode, gender_str)
        print(f"   [{i}/{len(files)}] Processing {f}...", end="", flush=True)

        try:
            if model == "qwen-vl":
                inputs = qwen_processor.apply_chat_template([{"role": "user", "content": prompt, "image": str(img_path)}], return_tensors="pt")
                inputs = inputs.to(qwen_model_obj.device)
                outputs = qwen_model_obj.generate(**inputs, max_new_tokens=256)
                caption = qwen_processor.decode(outputs[0], skip_special_tokens=True)
            else:
                with open(img_path, "rb") as ifile:
                    b64 = base64.b64encode(ifile.read()).decode('utf-8')
                res = client.chat(model='moondream', messages=[{'role': 'user', 'content': prompt, 'images': [b64]}], options={'timeout': 60})
                caption = res['message']['content'].replace('\n', ' ').strip()
        except Exception: caption = f"{trigger}, a {gender_str}."

        caption = clean_caption(caption, trigger)
        with open(txt_path, "w", encoding="utf-8") as tf: tf.write(caption)
        print(" Done.")
    print(f"✅ Captions complete.")