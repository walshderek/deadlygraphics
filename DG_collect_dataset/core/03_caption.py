import sys
import os
import base64
import ollama
import utils

OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434')
CAPTION_MODE = "fixed"

def generate_prompt(trigger, mode):
    base = f"The person in this image is named {trigger}. "
    if mode == "fixed":
        return (f"{base}\nDescribe the image for an AI training dataset.\n"
                f"RULES:\n1. Start the sentence exactly with '{trigger}, '.\n"
                f"2. Describe CLOTHING, BACKGROUND, POSE, LIGHTING.\n"
                f"3. Do NOT describe facial features, makeup, or hairstyle.\n"
                f"4. Keep it to one concise paragraph.")
    return base + " Describe everything."

def run(slug, model="moondream"):
    config = utils.load_config(slug)
    if not config: return
    trigger = config['trigger']
    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['crop']
    out_dir = path / utils.DIRS['caption']
    out_dir.mkdir(parents=True, exist_ok=True)
    
    ollama_client = None
    qwen_processor = None
    qwen_model = None
    
    if model == "qwen-vl":
        print("⏳ Loading Qwen-VL Model...")
        from transformers import QwenVLProcessor, QwenVLForConditionalGeneration
        import torch
        qwen_path = utils.ROOT_DIR / "models" / "qwen-vl"
        qwen_processor = QwenVLProcessor.from_pretrained(str(qwen_path), trust_remote_code=True)
        qwen_model = QwenVLForConditionalGeneration.from_pretrained(
            str(qwen_path), 
            device_map="auto" if torch.cuda.is_available() else "cpu", 
            trust_remote_code=True
        ).eval()
    else:
        try:
            ollama_client = ollama.Client(host=OLLAMA_HOST)
            ollama_client.ps()
        except:
            print("❌ Ollama connection failed."); return

    files = [f for f in os.listdir(in_dir) if f.lower().endswith('.jpg')]
    print(f"📝 Captioning {len(files)} images with {model}...")

    for i, f in enumerate(files, 1):
        txt_path = out_dir / (os.path.splitext(f)[0] + ".txt")
        if txt_path.exists(): continue
            
        img_path = in_dir / f
        caption = ""
        final_prompt = generate_prompt(trigger, CAPTION_MODE)
        
        if model == "qwen-vl":
            inputs = qwen_processor.apply_chat_template(
                [{"role": "user", "content": final_prompt, "image": str(img_path)}],
                return_tensors="pt"
            )
            inputs = inputs.to(qwen_model.device)
            outputs = qwen_model.generate(**inputs, max_new_tokens=256)
            caption = qwen_processor.decode(outputs[0], skip_special_tokens=True)
            if "concise paragraph." in caption:
                caption = caption.split("concise paragraph.")[-1].strip()
        else:
            with open(img_path, "rb") as ifile:
                b64 = base64.b64encode(ifile.read()).decode('utf-8')
            res = ollama_client.chat(
                model='moondream', 
                messages=[{'role': 'user', 'content': final_prompt, 'images': [b64]}],
                options={'timeout': 60}
            )
            caption = res['message']['content'].replace('\n', ' ').strip()

        if not caption.startswith(trigger):
            caption = f"{trigger}, {caption}"
            
        with open(txt_path, "w", encoding="utf-8") as tf:
            tf.write(caption)
        print(f"   [{i}/{len(files)}] Done.")