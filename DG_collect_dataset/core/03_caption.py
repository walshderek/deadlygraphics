import sys
import os
import base64
import utils

# --- CONFIGURATION ---
# If your Ollama is on a different server, change this IP!
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434')

# "fixed" = Don't describe hair/face (Good for Claudia Winkleman)
# "variable" = Describe hair/makeup (Good for actors/Ronaldo changing looks)
CAPTION_MODE = "fixed" 

try:
    import ollama
    client = ollama.Client(host=OLLAMA_HOST)
except ImportError:
    print("⚠️ Ollama library not found. Run: pip install ollama")
    client = None

def generate_prompt(trigger, mode):
    base_instr = f"The person in this image is named {trigger}. "
    
    if mode == "fixed":
        return (
            f"{base_instr}\n"
            f"Describe the image for an AI training dataset.\n"
            f"RULES:\n"
            f"1. Start the sentence exactly with '{trigger}, '.\n"
            f"2. Describe the CLOTHING, BACKGROUND, POSE, and LIGHTING in detail.\n"
            f"3. IMPORTANT: Do NOT describe the person's facial features, eye color, makeup, or hairstyle.\n"
            f"4. Keep it to one concise paragraph."
        )
    else:
        return (
            f"{base_instr}\n"
            f"Describe the image for an AI training dataset.\n"
            f"RULES:\n"
            f"1. Start the sentence exactly with '{trigger}, '.\n"
            f"2. Describe the CLOTHING, BACKGROUND, POSE, and LIGHTING.\n"
            f"3. Describe the HAIRSTYLE and FACIAL HAIR explicitly.\n"
            f"4. Do NOT describe the person's underlying facial structure (nose, eye shape).\n"
            f"5. Keep it to one concise paragraph."
        )

def run(project_slug):
    config = utils.load_config(project_slug)
    if not config:
        print("❌ Config missing.")
        return

    trigger = config['trigger']
    path = utils.get_project_path(project_slug)
    in_dir = path / utils.DIRS['crop']
    out_dir = path / utils.DIRS['caption']
    
    # Connection Check
    if client:
        try:
            client.ps() # Ping server
            print(f"✅ Connected to Ollama at {OLLAMA_HOST}")
        except Exception as e:
            print(f"❌ Could not connect to Ollama at {OLLAMA_HOST}")
            print(f"   Error: {e}")
            return

    if not in_dir.exists():
        print(f"❌ No crops found at {in_dir}")
        return

    files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    if not files:
        print(f"⚠️  No cropped images to caption.")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📝 Captioning {len(files)} images for {trigger} (Mode: {CAPTION_MODE})...")
    
    count = 0
    for f in files:
        img_path = in_dir / f
        txt_path = out_dir / (os.path.splitext(f)[0] + ".txt")
        
        if txt_path.exists():
            count += 1
            continue

        caption = ""
        
        if client:
            try:
                with open(img_path, "rb") as img_file:
                    b64_data = base64.b64encode(img_file.read()).decode('utf-8')
                
                final_prompt = generate_prompt(trigger, CAPTION_MODE)

                res = client.chat(
                    model='moondream', 
                    messages=[{'role': 'user', 'content': final_prompt, 'images': [b64_data]}]
                )
                caption = res['message']['content'].replace('\n', ' ').strip()
                
                if not caption.startswith(trigger):
                    caption = f"{trigger}, {caption}"
                    
            except Exception as e:
                print(f"   ⚠️ Ollama Error on {f}: {e}")
        
        if not caption:
            caption = f"{trigger}, a person."

        with open(txt_path, "w", encoding="utf-8") as tf:
            tf.write(caption)
        
        count += 1
        if count % 5 == 0: print(f"   Captioned {count}...")

    print(f"✅ Generated {count} captions.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])