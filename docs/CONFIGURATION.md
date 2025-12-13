# Deadly Graphics: Configuration Standards

This document defines the file paths, credential formats, and environment variables required to operate the "Diamond Stack".

## 1. The "One True Path" (Model Storage)
To prevent duplication and save WSL storage, all heavy model weights (Checkpoints, LoRAs, VAEs) reside on the high-speed Windows NVMe drive.

* **Windows Path:** \C:\AI\models\
* **WSL Path:** \/mnt/c/AI/models/\

All applications must be configured to read from this central repository.

## 2. AI-Toolkit Configuration (Flux/SDXL Training)

### Credentials
AI-Toolkit requires a Hugging Face token to download gated models (like Flux.1-dev).
* **File Location:** \/home/seanf/workspace/deadlygraphics/ai/apps/ai-toolkit/.env\
* **File Format:**
    \\\ash
    HF_TOKEN=hf_YourActualTokenHere
    \\\

### Cache Redirection (Crucial)
By default, AI-Toolkit (via Hugging Face) downloads models to \~/.cache\. We must redirect this to our central storage to prevent filling the WSL virtual disk.
* **Environment Variable:** \HF_HOME\
* **Target Path:** \/mnt/c/AI/models/huggingface\
* **Implementation:** Add \export HF_HOME="/mnt/c/AI/models/huggingface"\ to \~/.bashrc\.

## 3. ComfyUI Configuration

### External Models
ComfyUI must be told where the central models are located using the YAML config.
* **File:** \extra_model_paths.yaml\ (in ComfyUI root)
* **Configuration:**
    \\\yaml
    comfyui:
        base_path: /mnt/c/AI/models
        checkpoints: checkpoints
        clip: clip
        clip_vision: clip_vision
        configs: configs
        controlnet: controlnet
        embeddings: embeddings
        loras: loras
        upscale_models: upscale_models
        vae: vae
    \\\

## 4. OneTrainer Configuration
OneTrainer must be configured to point its model cache and concept folders to the central path.
* **Cache Path:** \/mnt/c/AI/models/huggingface\ (Shared with AI-Toolkit)
