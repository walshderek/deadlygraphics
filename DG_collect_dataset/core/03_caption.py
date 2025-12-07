# Script Name: core/03_caption.py
import sys
import os
import subprocess
import utils
from pathlib import Path
from PIL import Image

def check_deps():
    missing = []
    for p in ["torch", "transformers", "einops", "accelerate", "qwen_vl_utils"]:
        try: __import__(p.split('_')[0])
        except: missing.append(p)
    if missing:
        print(f"--> [03_caption] Installing deps...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
check_deps()

from transformers import AutoModelForCausalLM, AutoTokenizer, AutoProcessor
import torch

MODEL_ROOT = Path("/mnt/c/ai/models/LLM") if os.name != 'nt' else Path(r"C:\ai\models\LLM")

def load_model(model_name):
    if model_name == "moondream":
        path = MODEL_ROOT / "moondream2"
        if not path.exists(): path = "vikhyatk/moondream2"
        model = AutoModelForCausalLM.from_pretrained(path, trust_remote_code=True).to("cuda" if torch.cuda.is_available() else "cpu")
        tokenizer = AutoTokenizer.from_pretrained(path)
        return model, tokenizer, "moondream"
    # Qwen logic would go here
    return None, None, None

def generate_caption(img_path, model, processor, m_type, style, trigger):
    try:
        image = Image.open(img_path).convert("RGB")
        
        if style == "crinklypaper":
            prompt = f"""You are an expert captioner.
Rules:
1. Start with trigger word: "{trigger}".
2. Describe EVERYTHING: characters, clothing, background.
3. Be objective. No style mentions (anime, 2d).
4. Single paragraph."""
        else:
            prompt = f"Describe this image starting with {trigger}."

        if m_type == "moondream":
            enc = model.encode_image(image)
            return model.answer_question(enc, prompt, tokenizer=processor)
            
    except: return f"{trigger}, caption failed"

def run(slug, trigger_word="ohwx", model_name="moondream", style="crinklypaper"):
    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['crop']
    out_dir = path / utils.DIRS['caption']
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"--> Loading {model_name}...")
    llm, proc, mtype = load_model(model_name)
    if not llm: print("❌ Model failed."); return

    files = [f for f in os.listdir(in_dir) if f.endswith('.jpg')]
    print(f"📝 Captioning {len(files)} images...")

    for f in files:
        cap = generate_caption(in_dir / f, llm, proc, mtype, style, trigger_word)
        with open(out_dir / (os.path.splitext(f)[0] + ".txt"), "w", encoding="utf-8") as tf:
            tf.write(cap)

    print(f"✅ Captions Done.")