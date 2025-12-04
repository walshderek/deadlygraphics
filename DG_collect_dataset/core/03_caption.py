# Script Name: core/03_caption.py
import sys, os, utils, torch
from transformers import AutoModelForCausalLM, AutoProcessor
from PIL import Image

MODEL_ROOT = "/mnt/c/ai/models/LLM" if os.name != 'nt' else "C:/ai/models/LLM"

def run(slug, trigger_word="ohwx", model_name="moondream", style="crinklypaper"):
    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['crop']
    out_dir = path / utils.DIRS['caption']
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"--> Loading {model_name}...")
    # (Load model logic here - same as previous response)
    # ...
    print(f"--> Captioned images.")