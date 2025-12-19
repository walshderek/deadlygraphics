# DeadlyMusubi Quick Start Guide

Get up and running with DeadlyMusubi in under 10 minutes.

## Prerequisites

✅ NVIDIA RTX 3060 or better GPU
✅ Ubuntu 22.04 or WSL2
✅ Python 3.10+
✅ 32GB+ system RAM
✅ CUDA drivers installed

## Step 1: Choose Your Configuration

Based on your GPU:

| Your GPU | Recommended Config |
|----------|-------------------|
| RTX 3060 (12GB) | `cuda121_torch25_fp8_aggressive` |
| RTX 3070/3080 | `cuda121_torch25_fp8_aggressive` |
| RTX 4080 (16GB) | `cuda121_torch25_baseline` |
| RTX 4090 (24GB) | `cuda121_torch25_baseline` |

## Step 2: Create Virtual Environment

```bash
# Navigate to DeadlyMusubi
cd /path/to/deadlygraphics/DeadlyMusubi

# Create venv (example for RTX 4080)
python3 -m venv ~/venvs/deadly_musubi_baseline
source ~/venvs/deadly_musubi_baseline/bin/activate

# Install dependencies
pip install -r venv_configs/cuda121_torch25_baseline.txt
```

Or use the automated launcher:

```bash
./scripts/deadly_launcher.sh --config cuda121_torch25_baseline
```

## Step 3: Verify Installation

```bash
python3 << EOF
import torch
print(f"PyTorch: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"VRAM: {vram_gb:.1f} GB")
EOF
```

Expected output:
```
PyTorch: 2.5.1+cu121
CUDA Available: True
GPU: NVIDIA GeForce RTX 4080
VRAM: 16.0 GB
```

## Step 4: Prepare Your Dataset

Create a TOML configuration file for your dataset:

```toml
# ~/musubi-tuner/files/tomls/my_project.toml

[general]
resolution = 256
num_frames = 24

[[datasets]]
type = "video"
path = "/path/to/your/videos"
trigger_word = "ohwx"
num_repeats = 10
```

## Step 5: Run Training

Using the DeadlyMusubi training template:

```bash
# Activate your venv
source ~/venvs/deadly_musubi_baseline/bin/activate

# Navigate to Musubi Tuner
cd /path/to/musubi-tuner

# Copy and customize the template
cp /path/to/DeadlyMusubi/templates/deadly_wan_train.sh ./

# Edit the script with your paths
nano deadly_wan_train.sh

# Run training
./deadly_wan_train.sh my_project ohwx
```

## Step 6: Monitor Training

Watch GPU usage:
```bash
watch -n 1 nvidia-smi
```

Check for issues in log:
```bash
tail -f /mnt/c/AI/outputs/my_project/training_log_*.txt
```

## Troubleshooting

### OOM Error
1. Check [OOM_MITIGATION.md](docs/OOM_MITIGATION.md)
2. Switch to fp8_aggressive config
3. Reduce resolution to 224x224

### NaN in Loss
1. Check [NAN_PREVENTION.md](docs/NAN_PREVENTION.md)
2. Reduce learning rate to 0.00005
3. Increase warmup steps to 500

### Slow Performance (> 5 it/s)
1. Close other GPU applications
2. Check GPU isn't thermal throttling
3. Verify CUDA version matches PyTorch

## Performance Expectations

| GPU | Config | it/s | Training Time (256x256) |
|-----|--------|------|------------------------|
| RTX 3060 | fp8_aggressive | ~5.0 | ~3.8 hours |
| RTX 4080 | baseline | ~4.2 | ~3.5 hours |
| RTX 4090 | baseline | ~3.0 | ~2.5 hours |

## Next Steps

- Review [knowledge_base/proven_constants/](knowledge_base/proven_constants/) for verified configs
- Explore [knowledge_base/variables/](knowledge_base/variables/) for experimental optimizations
- Join the community to share your results
- Contribute new configurations back to the knowledge base

## Getting Help

1. Check the documentation in `DeadlyMusubi/docs/`
2. Review similar configurations in `knowledge_base/`
3. Check error logs carefully
4. Document your issue with full specs and error messages

## Success Criteria

✅ Training completes without OOM
✅ No NaN in loss values
✅ Training time < 4 hours for 256x256
✅ it/s < 5.0
✅ Output quality is good

Happy training! 🚀
