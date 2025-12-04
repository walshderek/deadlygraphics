# Script Name: core/06_publish.py
# Description: Prepares training files and logs to Google Sheets.

import sys
import os
import utils
import datetime
import pickle
import json
from pathlib import Path

SHEET_NAME = "DeadlyGraphics LoRA Tracker"

def log_to_sheet(slug, trigger, model):
    creds_file = Path(utils.CREDENTIALS_FILE) if hasattr(utils, 'CREDENTIALS_FILE') else Path("/mnt/c/credentials/credentials.json")
    # Need to find the Google client secret. Assuming it's defined in utils or we use a fixed path
    # For now, using the path you gave earlier:
    CLIENT_SECRET = Path("/mnt/c/AI/apps/ComfyUI Desktop/custom_nodes/comfyui-google-sheets-integration/client_secret.json")
    
    if not CLIENT_SECRET.exists():
        print(f"⚠️ Google Secrets not found at {CLIENT_SECRET}. Skipping log.")
        return

    try:
        import gspread
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        creds = None
        token_path = utils.ROOT_DIR / 'token.pickle'

        if token_path.exists():
            with open(token_path, 'rb') as token: creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
                creds = flow.run_console()
            with open(token_path, 'wb') as token: pickle.dump(creds, token)

        client = gspread.authorize(creds)
        try: sheet = client.open(SHEET_NAME).sheet1
        except: sheet = client.create(SHEET_NAME).sheet1; sheet.append_row(["Date", "Project", "Trigger", "Model", "Status"])

        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        sheet.append_row([ts, slug, trigger, model, "Ready"])
        print(f"✅ Logged to Google Sheet.")

    except Exception as e:
        print(f"❌ Logging failed: {e}")

def run(slug, trigger="ohwx", model="moondream"):
    print(f"🚀 Publishing {slug}...")
    
    # [Existing TOML/BAT generation logic goes here - assumed unchanged from previous working version]
    # ... (Keep your existing file generation code here if you have it, otherwise I can paste it back)
    
    # Log at the end
    log_to_sheet(slug, trigger, model)

if __name__ == "__main__":
    if len(sys.argv) > 1: run(sys.argv[1])