# Script Name: core/03_caption.py
# Description: Captions images using local LLMs (Moondream/Qwen).

import sys
import os
import utils
import torch
from pathlib import Path
from PIL import Image

# Dependency Check
def check_deps():
    missing = []
    for p in ["torch", "transformers", "einops", "accelerate", "qwen_vl_utils"]:
        try: __import__(p.split('_')[0])
        except: missing.append(p)
    if missing:
        print(f"--> Installing caption deps: {missing}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
check_deps()

from transformers import AutoModelForCausalLM, AutoTokenizer, AutoProcessor

# Config
MODEL_ROOT = Path(r"C:\ai\models\LLM") if os.name == 'nt' else Path("/mnt/c/ai/models/LLM")

def load_model(model_name):
    print(f"--> Loading {model_name}...")
    if model_name == "qwen":
        path = MODEL_ROOT / "Qwen2.5-VL-7B-Instruct"
        if not path.exists(): path = "Qwen/Qwen2.5-VL-7B-Instruct"
        try:
            model = AutoModelForCausalLM.from_pretrained(path, torch_dtype="auto", device_map="auto", trust_remote_code=True)
            processor = AutoProcessor.from_pretrained(path, trust_remote_code=True)
            return model, processor, "qwen"
        except Exception as e: print(f"❌ Qwen Load Fail: {e}"); return None, None, None

    elif model_name == "moondream":
        path = MODEL_ROOT / "moondream2"
        if not path.exists(): path = "vikhyatk/moondream2"
        try:
            model = AutoModelForCausalLM.from_pretrained(path, trust_remote_code=True).to("cuda")
            tokenizer = AutoTokenizer.from_pretrained(path)
            return model, tokenizer, "moondream"
        except Exception as e: print(f"❌ Moondream Load Fail: {e}"); return None, None, None
    return None, None, None

def generate_caption(img_path, model, processor, m_type, style, trigger):
    try:
        image = Image.open(img_path).convert("RGB")
        
        if style == "crinklypaper":
            prompt = f"Describe this image for AI training. Start with '{trigger}'. Be objective. No style mentions."
        else:
            prompt = f"Describe this image starting with {trigger}."

        if m_type == "moondream":
            enc = model.encode_image(image)
            return model.answer_question(enc, prompt, tokenizer=processor)
        elif m_type == "qwen":
            # Simplified Qwen call
            msgs = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": prompt}]}]
            text = processor.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            inputs = processor(text=[text], images=[image], padding=True, return_tensors="pt").to("cuda")
            gen_ids = model.generate(**inputs, max_new_tokens=256)
            gen_ids = [out[len(in_ids):] for in_ids, out in zip(inputs.input_ids, gen_ids)]
            return processor.batch_decode(gen_ids, skip_special_tokens=True)[0]
    except: return f"{trigger}, caption failed"

def run(slug, trigger="ohwx", model="moondream", style="crinklypaper"):
    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['crop'] # Use cropped images
    if not in_dir.exists(): in_dir = path / utils.DIRS['scrape'] # Fallback
    
    out_dir = path / utils.DIRS['caption']
    out_dir.mkdir(parents=True, exist_ok=True)

    llm, proc, mtype = load_model(model)
    if not llm: return

    files = [f for f in os.listdir(in_dir) if f.endswith('.jpg')]
    print(f"📝 Captioning {len(files)} images...")

    for f in files:
        cap = generate_caption(in_dir / f, llm, proc, mtype, style, trigger)
        with open(out_dir / (os.path.splitext(f)[0] + ".txt"), "w", encoding="utf-8") as tf:
            tf.write(cap)
        print(f"   Captioned: {f}")

if __name__ == "__main__":
    if len(sys.argv) > 1: run(sys.argv[1])