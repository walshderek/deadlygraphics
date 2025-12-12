import sys
import os
import time
import torch
import re
import importlib
from pathlib import Path

# --- BOOTSTRAP PATHS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
import utils

# Force localhost for WSL
OLLAMA_HOST = "http://127.0.0.1:11434"
os.environ["OLLAMA_HOST"] = OLLAMA_HOST
os.environ["OLLAMA_MODELS"] = str(utils.MODEL_STORE_ROOT)

def get_system_instruction(trigger, gender):
    return f"""
    Task: Describe the image for a Stable Diffusion dataset.
    Subject: The person in the image is '{trigger}'.
    
    CRITICAL RULES:
    1. START immediately with "{trigger}". Do NOT say "The image shows" or "The image features".
    2. NEVER say "a man named {trigger}" or "a person". Use the name '{trigger}' as the noun.
    3. NO MARKDOWN. Do not use bold (**text**) or italics.
    4. Disentangle the subject: Describe the clothing and background in extreme detail so the AI separates them from the face.
    
    BAD EXAMPLE (Do Not Do This):
    "The image features a man named {trigger} standing in a park. He is wearing a suit."

    GOOD EXAMPLE (Do This):
    "{trigger} is standing outdoors in a park with blurred green trees in the background. {trigger} is wearing a navy blue wool suit jacket, a white collared shirt, and a red silk tie with diagonal stripes. The lighting is soft and natural."
    """

def clean_caption(text, trigger):
    # 1. Kill the specific bad phrases if Qwen ignores us
    text = re.sub(r"(?i)^(the image features|the image shows|a photo of|an image of)\s*", "", text.strip())
    # 2. Remove Markdown bolding/italics
    text = text.replace("**", "").replace("*", "")
    # 3. Clean whitespace
    text = text.strip(" ,.:")
    # 4. Ensure it starts with trigger
    if not text.lower().startswith(trigger.lower()):
        text = f"{trigger}, {text}"
    return text

def run(slug):
    config = utils.load_config(slug)
    if not config: return
    
    trigger = config['trigger']
    gender = config.get('gender', 'm')
    model = config.get('model', 'qwen-vl')
    gender_str = 'man' if gender == 'm' else 'woman'

    path = utils.get_project_path(slug)
    
    # --- FIX: USE CORRECT DIR NAMES FROM UTILS ---
    # Prioritize 04_clean, fallback to 03_validate
    in_dir = path / utils.DIRS.get('clean', '04_clean')
    
    if not in_dir.exists():
        print(f"⚠️ '{in_dir.name}' not found. Checking validation folder...")
        in_dir = path / utils.DIRS.get('validate', '03_validate')
    
    if not in_dir.exists():
        print(f"❌ Error: No input images found in {path}")
        return

    print(f"📝 Captioning images in: {in_dir}...")
    
    # Qwen Setup (4-bit Turbo)
    if model == "qwen-vl":
        try:
            print("⏳ Loading Qwen2.5-VL...")
            from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
            
            qwen_path = utils.MODEL_STORE_ROOT / "QWEN" / "Qwen2.5-VL-3B-Instruct"
            
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4"
            )
            
            qwen_model_obj = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                str(qwen_path),
                quantization_config=bnb_config,
                device_map="auto",
            )
            qwen_processor = AutoProcessor.from_pretrained(str(qwen_path))
        except Exception as e:
            print(f"❌ Failed to load Qwen: {e}")
            return
    else:
        # Fallback setup if needed
        pass

    files = sorted([f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png'))])
    system_instruction = get_system_instruction(trigger, gender_str)

    for i, f in enumerate(files, 1):
        txt_path = in_dir / (os.path.splitext(f)[0] + ".txt")
        if txt_path.exists(): 
            continue
        
        print(f"   [{i}/{len(files)}] {f}...", end="", flush=True)
        
        try:
            # Inference Logic
            if model == "qwen-vl":
                from qwen_vl_utils import process_vision_info
                
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": str(in_dir/f), "max_pixels": 768*768},
                            {"type": "text", "text": system_instruction},
                        ],
                    }
                ]
                
                text_input = qwen_processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                image_inputs, video_inputs = process_vision_info(messages)
                
                inputs = qwen_processor(
                    text=[text_input],
                    images=image_inputs,
                    videos=video_inputs,
                    padding=True,
                    return_tensors="pt",
                ).to(qwen_model_obj.device)

                generated_ids = qwen_model_obj.generate(**inputs, max_new_tokens=256)
                
                generated_ids_trimmed = [
                    out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
                ]
                caption = qwen_processor.batch_decode(
                    generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
                )[0]
                
            else:
                caption = f"{trigger}, a {gender_str}."

            caption = clean_caption(caption, trigger)
            with open(txt_path, "w", encoding="utf-8") as tf: tf.write(caption)
            print(" Done.")
            
        except Exception as e:
            print(f" Error: {e}")

    print("✅ Captioning complete.")