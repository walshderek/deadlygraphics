import sys
import os
import base64
import time
import subprocess
import ollama
import utils
import re
import torch

# Force localhost for WSL
OLLAMA_HOST = "http://127.0.0.1:11434"
os.environ["OLLAMA_HOST"] = OLLAMA_HOST
os.environ["OLLAMA_MODELS"] = str(utils.MODEL_STORE_ROOT)

def ensure_ollama_server():
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        client.list() 
        return client
    except Exception: return None

def generate_prompt(trigger, mode, gender_str="person"):
    base = f"Photo of the face of {trigger}, a {gender_str}. "
    if mode == "fixed":
        return (f"{base}\nDescribe CLOTHING, BACKGROUND, POSE, and LIGHTING.\n"
                f"Do NOT describe facial features or hair.\n"
                f"Keep it concise.")
    return base + " Describe everything visible."

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
    
    # Qwen Setup
    qwen_model_obj = None
    qwen_processor = None
    
    if model == "qwen-vl":
        print("⏳ Loading Qwen2.5-VL Model (this may take a moment)...")
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
        from qwen_vl_utils import process_vision_info
        
        # Point to the NEW path in utils
        qwen_path = utils.MODEL_STORE_ROOT / "QWEN" / "Qwen2.5-VL-3B-Instruct"
        
        if not qwen_path.exists():
            print(f"❌ Qwen model not found at {qwen_path}. Run utils.bootstrap() first.")
            return

        try:
            qwen_model_obj = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                str(qwen_path),
                torch_dtype=torch.float16,
                device_map="auto",
            )
            qwen_processor = AutoProcessor.from_pretrained(str(qwen_path))
            print("✅ Qwen-VL Loaded on GPU.")
        except Exception as e:
            print(f"❌ Failed to load Qwen: {e}")
            return

    files = [f for f in os.listdir(in_dir) if f.lower().endswith('.jpg')]
    print(f"📝 Captioning {len(files)} images with {model}...")

    for i, f in enumerate(files, 1):
        txt_path = out_dir / (os.path.splitext(f)[0] + ".txt")
        if txt_path.exists(): continue
        
        img_path = in_dir / f
        caption = ""
        prompt = generate_prompt(trigger, mode, gender_str)
        print(f"   [{i}/{len(files)}] Processing {f}...", end="", flush=True)

        try:
            if model == "qwen-vl":
                # Qwen2.5-VL Logic
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": str(img_path)},
                            {"type": "text", "text": prompt},
                        ],
                    }
                ]
                
                text_input = qwen_processor.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
                
                image_inputs, video_inputs = process_vision_info(messages)
                inputs = qwen_processor(
                    text=[text_input],
                    images=image_inputs,
                    videos=video_inputs,
                    padding=True,
                    return_tensors="pt",
                )
                inputs = inputs.to(qwen_model_obj.device)

                generated_ids = qwen_model_obj.generate(**inputs, max_new_tokens=128)
                generated_ids_trimmed = [
                    out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
                ]
                caption = qwen_processor.batch_decode(
                    generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
                )[0]
                
            else:
                # MOONDREAM Fallback
                if not client: 
                    print(" (Ollama missing)"); continue
                with open(img_path, "rb") as ifile:
                    b64 = base64.b64encode(ifile.read()).decode('utf-8')
                res = client.chat(model='moondream', messages=[{'role': 'user', 'content': prompt, 'images': [b64]}], options={'timeout': 60})
                caption = res['message']['content'].replace('\n', ' ').strip()
        
        except Exception as e: 
            print(f" ⚠️ Error: {e}")
            caption = f"{trigger}, a {gender_str}."

        caption = clean_caption(caption, trigger)
        with open(txt_path, "w", encoding="utf-8") as tf: tf.write(caption)
        print(" Done.")
    print(f"✅ Captions complete.")