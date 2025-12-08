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

def generate_prompt(trigger, mode):
    base = f"The person in this image is named {trigger}. "
    if mode == "fixed":
        return (f"{base}\nDescribe the image for an AI training dataset.\n"
                f"RULES:\n"
                f"1. Start the sentence exactly with '{trigger}, '.\n"
                f"2. Describe CLOTHING, BACKGROUND, POSE, and LIGHTING.\n"
                f"3. Do NOT describe facial features, makeup, or hairstyle.\n"
                f"4. Keep it to one concise paragraph.")
    return base + " Describe everything."

def clean_caption(text, trigger):
    """Removes common model conversational filler."""
    prefixes = [
        "an ai training dataset shows",
        "the image shows",
        "the image features",
        "in this image,",
        "a photo of",
        "describe the image:"
    ]
    
    clean = text.strip()
    lower_clean = clean.lower()
    
    for p in prefixes:
        if lower_clean.startswith(p):
            # Slice off the prefix (case-insensitive match logic)
            clean = clean[len(p):].strip()
            # Handle connecting words like "shows a..."
            if clean.lower().startswith("shows "):
                clean = clean[6:].strip()
            # If it became empty or weird, reset
            if not clean:
                clean = text
            # Re-evaluate lower for next pass
            lower_clean = clean.lower()

    # Final cleanup
    clean = clean.lstrip(",. ")
    
    # Ensure it starts with trigger
    if not clean.lower().startswith(trigger.lower()):
        clean = f"{trigger}, {clean}"
        
    return clean

def run(slug, model="moondream", mode="fixed"):
    config = utils.load_config(slug)
    if not config: return
    trigger = config['trigger']
    path = utils.get_project_path(slug)
    
    in_dir = path / utils.DIRS['crop']
    out_dir = path / utils.DIRS['caption']
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Connection Check
    try:
        ollama_client = ollama.Client(host=OLLAMA_HOST)
        ollama_client.ps()
    except Exception:
        print("❌ Ollama connection failed. Run 'ollama serve'.")
        return

    files = [f for f in os.listdir(in_dir) if f.lower().endswith('.jpg')]
    print(f"📝 Captioning {len(files)} images with {model}...")

    # Qwen Setup
    qwen_processor, qwen_model_obj = None, None
    if model == "qwen-vl":
        from transformers import QwenVLProcessor, QwenVLForConditionalGeneration
        import torch
        qwen_path = utils.ROOT_DIR / "models" / "qwen-vl"
        qwen_processor = QwenVLProcessor.from_pretrained(str(qwen_path), trust_remote_code=True)
        qwen_model_obj = QwenVLForConditionalGeneration.from_pretrained(
            str(qwen_path), device_map="auto", trust_remote_code=True
        ).eval()

    for i, f in enumerate(files, 1):
        txt_path = out_dir / (os.path.splitext(f)[0] + ".txt")
        if txt_path.exists(): continue
            
        img_path = in_dir / f
        caption = ""
        prompt = generate_prompt(trigger, mode)
        
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
                # Qwen specific cleanup
                if "concise paragraph." in caption:
                    caption = caption.split("concise paragraph.")[-1].strip()
            else:
                # Moondream
                with open(img_path, "rb") as ifile:
                    b64 = base64.b64encode(ifile.read()).decode('utf-8')
                
                res = ollama_client.chat(
                    model='moondream',
                    messages=[{'role': 'user', 'content': prompt, 'images': [b64]}],
                    options={'timeout': 60}
                )
                caption = res['message']['content'].replace('\n', ' ').strip()
                
        except Exception as e:
            print(f" ⚠️ Error: {e}")
            caption = f"{trigger}, a person."

        # Post-Process Cleaning
        caption = clean_caption(caption, trigger)

        with open(txt_path, "w", encoding="utf-8") as tf:
            tf.write(caption)
        
        print(" Done.")

    print(f"✅ Captions complete.")