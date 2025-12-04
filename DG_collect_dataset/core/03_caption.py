# Script Name: core/03_caption.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: Captions images using local LLMs (Moondream/Qwen).

import sys
import os
import subprocess
import utils
from pathlib import Path

# --- Dependency Check ---
def check_deps():
    missing = []
    try: import torch
    except ImportError: missing.append("torch")
    try: import transformers
    except ImportError: missing.append("transformers")
    try: import einops
    except ImportError: missing.append("einops")
    
    if missing:
        print(f"--> [03_caption] Installing missing deps: {', '.join(missing)}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)

check_deps()

from transformers import AutoModelForCausalLM, AutoTokenizer, AutoProcessor
import torch
from PIL import Image

# --- CONFIGURATION ---
# Default Model Path (WSL mapped to Windows)
MODEL_ROOT = Path("/mnt/c/ai/models/LLM") if os.name != 'nt' else Path(r"C:\ai\models\LLM")

def load_model(model_name):
    print(f"--> Loading {model_name}...")
    
    if model_name == "qwen":
        path = MODEL_ROOT / "Qwen2.5-VL-7B-Instruct"
        if not path.exists():
            print(f"⚠️ Model not found at {path}. Using HuggingFace Hub (Download might be slow).")
            path = "Qwen/Qwen2.5-VL-7B-Instruct"
        
        try:
            model = AutoModelForCausalLM.from_pretrained(
                path, torch_dtype="auto", device_map="auto", trust_remote_code=True
            )
            processor = AutoProcessor.from_pretrained(path, trust_remote_code=True)
            return model, processor, "qwen"
        except Exception as e:
            print(f"❌ Failed to load Qwen: {e}")
            return None, None, None

    elif model_name == "moondream":
        path = MODEL_ROOT / "moondream2"
        if not path.exists():
            path = "vikhyatk/moondream2"

        try:
            model = AutoModelForCausalLM.from_pretrained(path, trust_remote_code=True).to("cuda" if torch.cuda.is_available() else "cpu")
            tokenizer = AutoTokenizer.from_pretrained(path)
            return model, tokenizer, "moondream"
        except Exception as e:
            print(f"❌ Failed to load Moondream: {e}")
            return None, None, None
            
    return None, None, None

def generate_caption(image_path, model, processor, model_type, style="dg_char", trigger="ohwx"):
    try:
        image = Image.open(image_path).convert("RGB")
        
        if style == "crinklypaper":
            prompt = f"""
            Describe this image for AI training.
            Rules:
            1. Start with trigger word: "{trigger}".
            2. Describe EVERYTHING: characters, clothing, background, lighting, camera angle.
            3. Be objective.
            4. DO NOT mention art style, anime, cartoon, or 2d.
            5. Single paragraph.
            """
        else:
            prompt = f"Describe this image in detail, starting with {trigger}, focus on physical appearance and clothing."

        if model_type == "moondream":
            enc_image = model.encode_image(image)
            caption = model.answer_question(enc_image, prompt, tokenizer=processor)
            
        elif model_type == "qwen":
            messages = [{
                "role": "user", 
                "content": [{"type": "image", "image": image}, {"type": "text", "text": prompt}]
            }]
            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = processor(text=[text], images=[image], padding=True, return_tensors="pt").to("cuda")
            
            generated_ids = model.generate(**inputs, max_new_tokens=256)
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            caption = processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

        return caption.strip()

    except Exception as e:
        print(f"   ⚠️ Caption Error: {e}")
        return f"{trigger}, a person"

def run(project_slug, trigger_word="ohwx", model_name="moondream", style="crinklypaper"):
    path = utils.get_project_path(project_slug)
    in_dir = path / utils.DIRS['crop']
    out_dir = path / utils.DIRS['caption']
    
    if not in_dir.exists():
        print(f"❌ No crops found at {in_dir}. Run Step 2 first.")
        return

    # Load Model once
    model, processor, m_type = load_model(model_name)
    if not model:
        print("❌ Model failed to load. Exiting.")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    
    print(f"📝 Captioning {len(files)} images...")
    
    count = 0
    for f in files:
        img_path = in_dir / f
        txt_path = out_dir / (os.path.splitext(f)[0] + ".txt")
        
        # Skip if exists? (Optional, maybe force overwrite)
        # if txt_path.exists(): continue

        cap = generate_caption(img_path, model, processor, m_type, style, trigger_word)
        
        with open(txt_path, "w", encoding="utf-8") as tf:
            tf.write(cap)
        
        count += 1
        if count % 5 == 0: print(f"   Captioned {count}...")

    print(f"✅ Generated {count} captions.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])
    else:
        print("Usage: python 03_caption.py <slug>")