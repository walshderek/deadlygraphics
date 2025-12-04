# Script Name: DG_collect_dataset.py
# Authors: DeadlyGraphics, Gemini, ChatGPT
# Description: AI Dataset Factory. Bing Scraper + LLM Captioning + Google Sheets Logging.

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
from pathlib import Path

# --- Configuration ---
DEFAULT_SEARCH_TERM = "portrait photo"
TRIGGER_WORD = "ohwx"
MAX_IMAGES = 50
MAX_WORKERS = 5
SHEET_NAME = "DeadlyGraphics LoRA Tracker" 

if os.name == 'nt':
    WIN_MODEL_PATH = r"C:\ai\models\LLM"
    GOOGLE_CREDENTIALS_PATH = r"C:\AI\apps\ComfyUI Desktop\custom_nodes\comfyui-google-sheets-integration\client_secret.json"
else:
    WSL_MODEL_PATH = "/mnt/c/ai/models/LLM"
    GOOGLE_CREDENTIALS_PATH = "/mnt/c/AI/apps/ComfyUI Desktop/custom_nodes/comfyui-google-sheets-integration/client_secret.json"

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def log(msg):
    print(f"--> {msg}")

def get_model_dir():
    return WSL_MODEL_PATH if os.name != 'nt' else WIN_MODEL_PATH

# --- Dependency Management ---
def check_and_install_dependencies():
    required = [
        'requests', 'tqdm', 'beautifulsoup4', 'Pillow', 
        'opencv-python-headless', 'torch', 'transformers', 
        'einops', 'accelerate', 'qwen_vl_utils', 'gspread', 
        'oauth2client', 'google-auth-oauthlib', 'google-auth-httplib2'
    ]
    
    missing = []
    for pkg in required:
        try:
            import_name = pkg.split('-')[0]
            if pkg == 'beautifulsoup4': import_name = 'bs4'
            if pkg == 'Pillow': import_name = 'PIL'
            if pkg == 'opencv-python-headless': import_name = 'cv2'
            if pkg == 'qwen_vl_utils': import_name = 'qwen_vl_utils'
            if 'google' in pkg: import_name = pkg.replace('-', '_')
            __import__(import_name)
        except ImportError:
            missing.append(pkg)
            
    if missing:
        log(f"Installing: {', '.join(missing)}")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
        except:
            print("Manual Install Required."); sys.exit(1)

# --- Google Sheets ---
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

        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = None
        token_path = 'token.pickle'

        if os.path.exists(token_path):
            with open(token_path, 'rb') as token: creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDENTIALS_PATH, SCOPES)
                creds = flow.run_console() 
            with open(token_path, 'wb') as token: pickle.dump(creds, token)

        client = gspread.authorize(creds)
        try:
            sheet = client.open(SHEET_NAME).sheet1
        except gspread.SpreadsheetNotFound:
            log(f"⚠️ Sheet '{SHEET_NAME}' not found. Creating...")
            sheet = client.create(SHEET_NAME).sheet1
            sheet.append_row(["Timestamp", "Project Name", "Trigger Word", "Image Count", "Model", "Status"])

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, project_name, trigger_word, image_count, model_used, "Ready"])
        log(f"✅ Logged '{project_name}' to Sheet.")

    except Exception as e:
        log(f"❌ Logging Failed: {e}")

# --- Logic ---
def determine_output_dir(search_term):
    folder_name = re.sub(r'[\\/*?:"<>|]', "", search_term).replace(" ", "_")
    windows_drive = f"/mnt/h/My Drive/AI/Datasets/{folder_name}"
    if os.path.exists("/mnt/h"):
        try: os.makedirs(windows_drive, exist_ok=True); return windows_drive
        except: pass
    local_dir = f"datasets/{folder_name}"
    os.makedirs(local_dir, exist_ok=True); return local_dir

def fetch_bing_images(query, limit):
    log(f"Searching Bing: '{query}'")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    url = f"https://www.bing.com/images/async?q={query}&first=0&count={limit}&adlt=off"
    try:
        r = requests.get(url, headers=headers)
        return re.findall(r'murl&quot;:&quot;(.*?)&quot;', r.text)[:limit]
    except: return []

def download_worker(url, output_dir, index):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200: return None
        from PIL import Image
        img = Image.open(BytesIO(r.content)).convert("RGB")
        
        # Resize to 1024
        ratio = max(1024/img.width, 1024/img.height)
        new_size = (int(img.width*ratio), int(img.height*ratio))
        img = img.resize(new_size, Image.LANCZOS)
        
        # Center Crop
        left = (new_size[0] - 1024)/2; top = (new_size[1] - 1024)/2
        img = img.crop((left, top, left+1024, top+1024))

        path = os.path.join(output_dir, f"img_{index:04d}.jpg")
        img.save(path, "JPEG", quality=95)
        return path
    except: return None

def load_llm(model_type):
    from transformers import AutoModelForCausalLM, AutoTokenizer, AutoProcessor
    model_dir = get_model_dir()
    
    if model_type == "qwen":
        path = os.path.join(model_dir, "Qwen2.5-VL-7B-Instruct")
        if not os.path.exists(path): path = "Qwen/Qwen2.5-VL-7B-Instruct"
        try:
            model = AutoModelForCausalLM.from_pretrained(path, device_map="auto", trust_remote_code=True)
            processor = AutoProcessor.from_pretrained(path, trust_remote_code=True)
            return model, processor, "qwen"
        except Exception as e: log(f"Qwen Load Fail: {e}"); return None, None, None

    elif model_type == "moondream":
        path = os.path.join(model_dir, "moondream2")
        if not os.path.exists(path): path = "vikhyatk/moondream2"
        try:
            model = AutoModelForCausalLM.from_pretrained(path, trust_remote_code=True).to("cuda")
            tokenizer = AutoTokenizer.from_pretrained(path)
            return model, tokenizer, "moondream"
        except Exception as e: log(f"Moondream Fail: {e}"); return None, None, None

    return None, None, None

def generate_caption(image_path, model, processor, model_type, style, trigger):
    from PIL import Image
    try:
        image = Image.open(image_path).convert("RGB")
        if style == "crinklypaper":
            prompt = f"Describe this image for AI training. Start with '{trigger}'. Be objective. No style mentions."
        else:
            prompt = f"Describe this image starting with {trigger}."

        if model_type == "moondream":
            enc_image = model.encode_image(image)
            caption = model.answer_question(enc_image, prompt, tokenizer=processor)
        elif model_type == "qwen":
            # Simplified Qwen Inference
            messages = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": prompt}]}]
            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = processor(text=[text], images=[image], padding=True, return_tensors="pt").to("cuda")
            generated_ids = model.generate(**inputs, max_new_tokens=256)
            generated_ids_trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
            caption = processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

        return caption.strip()
    except: return f"{trigger}, caption failed"

def main():
    check_and_install_dependencies()
    parser = argparse.ArgumentParser()
    parser.add_argument("search_term", nargs="?", default=DEFAULT_SEARCH_TERM)
    parser.add_argument("--count", type=int, default=MAX_IMAGES)
    parser.add_argument("--trigger", default=TRIGGER_WORD)
    parser.add_argument("--model", choices=["qwen", "moondream"], default="moondream")
    parser.add_argument("--style", default="crinklypaper")
    parser.add_argument("steps", nargs="*")
    args = parser.parse_args()

    run_all = not args.steps
    steps_to_run = []
    if args.steps:
        for s in args.steps:
            parts = s.split(',')
            for p in parts:
                if '-' in p:
                    start, end = map(int, p.split('-'))
                    steps_to_run.extend(range(start, end + 1))
                else: steps_to_run.append(int(p))
    else: steps_to_run = [1, 2, 3, 6]

    output_dir = determine_output_dir(args.search_term)
    downloaded_files = []

    if 1 in steps_to_run:
        log(f"Output: {output_dir}")
        urls = fetch_bing_images(args.search_term, args.count)
        if not urls: log("No images found."); sys.exit(1)
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = [ex.submit(download_worker, u, output_dir, i) for i, u in enumerate(urls)]
            for f in concurrent.futures.as_completed(futures):
                if f.result(): downloaded_files.append(f.result())
        log(f"Downloaded {len(downloaded_files)} images.")
    else:
        if os.path.exists(output_dir):
             downloaded_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(".jpg")]

    if 3 in steps_to_run and downloaded_files:
        log(f"Initializing {args.model}...")
        model, processor, m_type = load_llm(args.model)
        if model:
            for img_path in downloaded_files:
                cap = generate_caption(img_path, model, processor, m_type, args.style, args.trigger)
                with open(os.path.splitext(img_path)[0] + ".txt", "w", encoding="utf-8") as f: f.write(cap)
                log(f"Captioned: {os.path.basename(img_path)}")

    if 6 in steps_to_run:
        log_to_google_sheet(args.search_term, args.trigger, len(downloaded_files), args.model)

    log("✅ Pipeline Complete.")

if __name__ == "__main__":
    main()