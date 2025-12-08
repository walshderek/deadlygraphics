import sys
import os
import base64
import time
import torch
import utils
import re

# Force localhost for WSL
OLLAMA_HOST = "http://127.0.0.1:11434"
os.environ["OLLAMA_HOST"] = OLLAMA_HOST
os.environ["OLLAMA_MODELS"] = str(utils.MODEL_STORE_ROOT)

# ================= THE AGGRESSIVE INSTRUCTION =================
# This uses "Few-Shot" logic to force Qwen to obey the format.
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

def ensure_ollama_server():
    import ollama
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        client.list() 
        return client
    except Exception: return None

def clean_caption(text, trigger):
    # 1. Kill the specific bad phrases if Qwen ignores us
    text = re.sub(r"(?i)^(the image features|the image shows|a photo of|an image of)\s*", "", text.strip())
    
    # 2. Remove Markdown bolding/italics
    text = text.replace("**", "").replace("*", "")
    
    # 3. Clean whitespace
    text = text.strip(" ,.:")
    
    # 4. Ensure it starts with trigger, but don't double up
    if not text.lower().startswith(trigger.lower()):
        text = f"{trigger}, {text}"
        
    return text

def run(slug, model="qwen-vl", mode="fixed"):
    config = utils.load_config(slug)
    if not config: return
    
    trigger = config['trigger']
    gender_str = {'m': 'man', 'f': 'woman'}.get(config.get('gender', 'm'), 'person')

    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['crop']
    out_dir = path / utils.DIRS['caption']
    out_dir.mkdir(parents=True, exist_ok=True)

    # ================= LOAD QWEN (4-BIT TURBO) =================
    qwen_model_obj = None
    qwen_processor = None
    client = None

    if model == "qwen-vl":
        print("⏳ Loading Qwen2.5-VL (Turbo 4-bit)...")
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
        from qwen_vl_utils import process_vision_info
        
        # Adjust this path if your Qwen is stored differently
        qwen_path = utils.MODEL_STORE_ROOT / "QWEN" / "Qwen2.5-VL-3B-Instruct" 
        
        if not qwen_path.exists():
            print(f"❌ Qwen model not found at {qwen_path}. Run utils.bootstrap() first.")
            return

        try:
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
            print("✅ Qwen-VL Loaded (4-bit Turbo).")
        except Exception as e:
            print(f"❌ Failed to load Qwen: {e}")
            return
    else:
        # Fallback to Ollama if not using Qwen-VL
        client = ensure_ollama_server()

    # ================= PROCESS IMAGES =================
    files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    print(f"📝 Captioning {len(files)} images with {model}...")

    # Get the perfect instruction
    system_instruction = get_system_instruction(trigger, gender_str)

    for i, f in enumerate(files, 1):
        txt_path = out_dir / (os.path.splitext(f)[0] + ".txt")
        if txt_path.exists(): 
            continue
        
        img_path = in_dir / f
        caption = ""
        print(f"   [{i}/{len(files)}] Processing {f}...", end="", flush=True)
        
        start_t = time.time()

        try:
            if model == "qwen-vl":
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image", 
                                "image": str(img_path),
                                "max_pixels": 768 * 768 
                            },
                            {"type": "text", "text": system_instruction},
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

                # Increased max_new_tokens to 256 for detailed T5 style description
                generated_ids = qwen_model_obj.generate(**inputs, max_new_tokens=256)
                
                generated_ids_trimmed = [
                    out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
                ]
                caption = qwen_processor.batch_decode(
                    generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
                )[0]
                
            else:
                # Legacy Moondream/Ollama logic
                if not client: continue
                with open(img_path, "rb") as ifile:
                    b64 = base64.b64encode(ifile.read()).decode('utf-8')
                simple_prompt = f"Describe this image of {trigger}. Focus on clothing and background."
                res = client.chat(model='moondream', messages=[{'role': 'user', 'content': simple_prompt, 'images': [b64]}], options={'timeout': 60})
                caption = res['message']['content'].replace('\n', ' ').strip()
        
        except Exception as e: 
            print(f" ⚠️ Error: {e}")
            caption = f"{trigger}, a {gender_str}."

        # Final cleanup and save
        caption = clean_caption(caption, trigger)
        with open(txt_path, "w", encoding="utf-8") as tf: tf.write(caption)
        
        elapsed = time.time() - start_t
        print(f" Done ({elapsed:.1f}s).")

    print(f"✅ Captions complete.")