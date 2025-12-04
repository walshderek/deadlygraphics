# Script Name: DG_collect_dataset.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: AI Dataset Factory. Scrapes -> Crops -> Captions (Qwen/Moondream) -> Logs to Google Sheets.

import sys
import os
import subprocess
import time
import shutil
import logging
import argparse
import concurrent.futures
import requests
import re
import platform
import json
import datetime
from urllib.parse import urlparse, unquote
from io import BytesIO

# --- Configuration ---
DEFAULT_SEARCH_TERM = "portrait photo"
TRIGGER_WORD = "ohwx" # Default trigger word
MAX_IMAGES = 50
MAX_WORKERS = 5

# LLM Paths (Cross-Platform)
if os.name == 'nt':
    WIN_MODEL_PATH = r"C:\ai\models\LLM"
    GOOGLE_CREDENTIALS_PATH = r"C:\AI\apps\ComfyUI Desktop\custom_nodes\comfyui-google-sheets-integration\client_secret.json"
else:
    WSL_MODEL_PATH = "/mnt/c/ai/models/LLM"
    # Translate Windows path to WSL
    GOOGLE_CREDENTIALS_PATH = "/mnt/c/AI/apps/ComfyUI Desktop/custom_nodes/comfyui-google-sheets-integration/client_secret.json"

# Google Sheet Name (Share your sheet with the client_email from the json if using service account, 
# or ensure your user has access if using OAuth client ID flow - OAuth flow requires browser interaction once)
# Since you provided a client_secret.json for an installed app, we will use a flow that might pop up a browser or provide a link.
# Ideally, for a headless script, a Service Account is better, but we will work with what you have.
SHEET_NAME = "DeadlyGraphics LoRA Tracker" 

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def log(msg):
    print(f"--> {msg}")

def get_os_type():
    if platform.system() == "Windows": return "WIN"
    if "microsoft" in platform.uname().release.lower(): return "WSL"
    return "LINUX"

def get_model_dir():
    if get_os_type() == "WSL":
        return WSL_MODEL_PATH
    return WIN_MODEL_PATH

# --- Dependency Management ---
def check_and_install_dependencies():
    # Added: gspread, oauth2client, google-auth-oauthlib, google-auth-httplib2
    required = [
        'requests', 'tqdm', 'beautifulsoup4', 'Pillow', 
        'opencv-python-headless', 'torch', 'transformers', 
        'einops', 'accelerate', 'qwen_vl_utils', 'gspread', 
        'oauth2client', 'google-auth-oauthlib', 'google-auth-httplib2'
    ]
    
    missing = []
    for pkg in required:
        try:
            import_name = pkg
            if pkg == 'beautifulsoup4': import_name = 'bs4'
            if pkg == 'Pillow': import_name = 'PIL'
            if pkg == 'opencv-python-headless': import_name = 'cv2'
            if pkg == 'qwen_vl_utils': import_name = 'qwen_vl_utils'
            if pkg == 'google-auth-oauthlib': import_name = 'google_auth_oauthlib'
            if pkg == 'google-auth-httplib2': import_name = 'google_auth_httplib2'
            __import__(import_name)
        except ImportError:
            missing.append(pkg)
            
    if missing:
        log(f"Installing dependencies: {', '.join(missing)}")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--no-cache-dir'] + missing)
        except:
            print("\n❌ Auto-install failed. Run manually:")
            print(f"{sys.executable} -m pip install {' '.join(missing)}")
            sys.exit(1)

# --- Google Sheets Integration ---
def log_to_google_sheet(project_name, trigger_word, image_count, model_used):
    log("Logging to Google Sheets...")
    
    if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
        log(f"❌ Google Credentials not found at: {GOOGLE_CREDENTIALS_PATH}")
        return

    try:
        import gspread
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        import pickle

        # Scopes required
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        
        creds = None
        token_path = 'token.pickle' # Save token locally to avoid re-auth

        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # This flow opens a browser. If headless (WSL), it might give a URL to click.
                flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDENTIALS_PATH, SCOPES)
                # run_console() is better for WSL/Remote
                creds = flow.run_console() 
            
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

        client = gspread.authorize(creds)
        
        try:
            sheet = client.open(SHEET_NAME).sheet1
        except gspread.SpreadsheetNotFound:
            log(f"⚠️ Sheet '{SHEET_NAME}' not found. Creating it...")
            sheet = client.create(SHEET_NAME).sheet1
            sheet.append_row(["Timestamp", "Project Name", "Trigger Word", "Image Count", "Model", "Status"])

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, project_name, trigger_word, image_count, model_used, "Ready for Training"])
        log(f"✅ Successfully logged '{project_name}' to Google Sheet.")

    except Exception as e:
        log(f"❌ Google Sheets Logging Failed: {e}")


# --- Image Processing (OpenCV/PIL) ---
def process_image(image_path):
    """Resizes and Crops image to be training friendly."""
    try:
        from PIL import Image, ImageOps
        
        img = Image.open(image_path)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        
        target_size = 1024
        
        ratio = max(target_size / img.size[0], target_size / img.size[1])
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)
        
        left = (new_size[0] - target_size) / 2
        top = (new_size[1] - target_size) / 2
        right = (new_size[0] + target_size) / 2
        bottom = (new_size[1] + target_size) / 2
        
        img = img.crop((left, top, right, bottom))
        img.save(image_path, "JPEG", quality=95)
        return True
    except Exception as e:
        log(f"Image processing failed: {e}")
        return False

# --- LLM Captioning ---
def load_llm(model_type="moondream"):
    from transformers import AutoModelForCausalLM, AutoTokenizer, AutoProcessor
    import torch

    model_dir = get_model_dir()
    
    if model_type == "qwen":
        path = os.path.join(model_dir, "Qwen2.5-VL-7B-Instruct")
        if not os.path.exists(path):
            log(f"⚠️ Qwen model not found at {path}. Falling back to download.")
            path = "Qwen/Qwen2.5-VL-7B-Instruct"
        
        log(f"Loading Qwen from {path}...")
        try:
            model = AutoModelForCausalLM.from_pretrained(
                path, torch_dtype="auto", device_map="auto", trust_remote_code=True
            )
            processor = AutoProcessor.from_pretrained(path, trust_remote_code=True)
            return model, processor, "qwen"
        except Exception as e:
            log(f"Failed to load Qwen: {e}")
            return None, None, None

    elif model_type == "moondream":
        path = os.path.join(model_dir, "moondream2")
        if not os.path.exists(path):
            path = "vikhyatk/moondream2"

        log(f"Loading Moondream from {path}...")
        try:
            model = AutoModelForCausalLM.from_pretrained(path, trust_remote_code=True).to("cuda")
            tokenizer = AutoTokenizer.from_pretrained(path)
            return model, tokenizer, "moondream"
        except Exception as e:
            log(f"Failed to load Moondream: {e}")
            return None, None, None
    
    return None, None, None

def generate_caption(image_path, model, processor, model_type, style="dg_char", trigger=TRIGGER_WORD):
    from PIL import Image
    try:
        image = Image.open(image_path).convert("RGB")
        
        if style == "crinklypaper":
            prompt = f"""
            You are an expert captioner. Describe this image for AI training.
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
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]
            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = processor(text=[text], images=[image], padding=True, return_tensors="pt").to("cuda")
            
            generated_ids = model.generate(**inputs, max_new_tokens=256)
            generated_ids_trimmed = [
                out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            caption = processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

        return caption.strip()

    except Exception as e:
        log(f"Captioning failed: {e}")
        return f"{trigger}, failed to caption"

# --- Main Pipeline ---
def determine_output_dir(search_term):
    folder_name = re.sub(r'[\\/*?:"<>|]', "", search_term).replace(" ", "_")
    windows_drive = f"/mnt/h/My Drive/AI/Datasets/{folder_name}"
    if os.path.exists("/mnt/h"):
        try: os.makedirs(windows_drive, exist_ok=True); return windows_drive
        except: pass
    local_dir = f"datasets/{folder_name}"
    os.makedirs(local_dir, exist_ok=True)
    return local_dir

def fetch_bing_images(query, limit):
    log(f"Searching Bing for: '{query}'...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    url = f"https://www.bing.com/images/async?q={query}&first=0&count={limit}&adlt=off"
    try:
        r = requests.get(url, headers=headers)
        links = re.findall(r'murl&quot;:&quot;(.*?)&quot;', r.text)
        return links[:limit]
    except Exception as e:
        log(f"Search failed: {e}"); return []

def download_worker(url, output_dir, index):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200: return None
        from PIL import Image
        img = Image.open(BytesIO(r.content))
        filename = f"image_{index:04d}.jpg"
        save_path = os.path.join(output_dir, filename)
        img.convert("RGB").save(save_path, "JPEG", quality=100)
        process_image(save_path)
        return save_path
    except: return None

def main():
    check_and_install_dependencies()
    
    parser = argparse.ArgumentParser()
    parser.add_argument("search_term", nargs="?", default=DEFAULT_SEARCH_TERM)
    parser.add_argument("--count", type=int, default=MAX_IMAGES)
    parser.add_argument("--caption_style", choices=["dg_char", "crinklypaper"], default="crinklypaper")
    parser.add_argument("--model", choices=["qwen", "moondream"], default="moondream")
    parser.add_argument("--skip_caption", action="store_true")
    # Add explicit trigger word argument, defaults to config TRIGGER_WORD if not set
    parser.add_argument("--trigger", default=TRIGGER_WORD, help="Trigger word for the LoRA")
    
    # Step control flags
    parser.add_argument("steps", nargs="*", help="Steps to run (e.g., 1 2,5). If empty, runs all.")
    
    args = parser.parse_args()

    # Determine which steps to run
    # 1: Scrape & Download
    # 2: Process (Crop/Resize) - Currently integrated into download, but could be separate
    # 3: Caption
    # 6: Publish (Log to Sheet) - Matching your request for "step 6"
    
    run_all = not args.steps
    steps_to_run = []
    if args.steps:
        # Handle comma separated or space separated
        for s in args.steps:
            parts = s.split(',')
            for p in parts:
                if '-' in p:
                    start, end = map(int, p.split('-'))
                    steps_to_run.extend(range(start, end + 1))
                else:
                    steps_to_run.append(int(p))
    else:
        steps_to_run = [1, 2, 3, 6] # Default flow

    # 1. Setup & Download
    output_dir = determine_output_dir(args.search_term)
    downloaded_files = []
    
    if 1 in steps_to_run:
        log(f"Output: {output_dir}")
        urls = fetch_bing_images(args.search_term, args.count)
        if not urls: log("No images found."); sys.exit(1)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(download_worker, url, output_dir, i) for i, url in enumerate(urls)]
            for f in concurrent.futures.as_completed(futures):
                path = f.result()
                if path: downloaded_files.append(path)
        log(f"Downloaded {len(downloaded_files)} images.")
    else:
        # If skipping download, assume files exist in output_dir for captioning
        if os.path.exists(output_dir):
             downloaded_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(".jpg")]

    # 2. Process (Currently part of download, but logically step 2)
    # If we skipped step 1 but want step 2, we'd re-process here. 
    # For now, assuming step 1 includes basic processing.

    # 3. Captioning
    if 3 in steps_to_run and not args.skip_caption and downloaded_files:
        log(f"Initializing {args.model} for captioning...")
        model, processor, m_type = load_llm(args.model)
        
        if model:
            log(f"Captioning with style: {args.caption_style}")
            for img_path in downloaded_files:
                cap = generate_caption(img_path, model, processor, m_type, args.caption_style, args.trigger)
                txt_path = os.path.splitext(img_path)[0] + ".txt"
                with open(txt_path, "w", encoding="utf-8") as f: f.write(cap)
                log(f"Captioned: {os.path.basename(img_path)}")
        else:
            log("❌ Could not load LLM. Skipping captions.")

    # 6. Publish / Log
    if 6 in steps_to_run:
        log_to_google_sheet(args.search_term, args.trigger, len(downloaded_files), args.model)

    log("✅ Dataset Pipeline Complete.")

if __name__ == "__main__":
    main()