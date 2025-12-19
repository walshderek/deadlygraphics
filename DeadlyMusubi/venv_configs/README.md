# DeadlyMusubi Virtual Environment Configurations

This directory contains specifications for different virtual environment setups optimized for Wan 2.2 training on various hardware configurations.

## Available Configurations

### Baseline Configurations (Recommended Start)
- `cuda121_torch25_baseline.txt` - Standard configuration for RTX 4080/4090
- `cuda118_torch20_legacy.txt` - Legacy configuration for older setups

### Memory-Optimized Configurations
- `cuda121_torch25_fp8_aggressive.txt` - Maximum memory savings for 12-16GB VRAM
- `cuda121_torch25_memory_optimized.txt` - Balanced memory/performance

### Performance-Optimized Configurations
- `cuda121_torch25_compiled.txt` - With torch.compile for maximum speed
- `cuda121_torch25_xformers.txt` - With xformers for attention optimization

## Usage

### Creating a Virtual Environment

```bash
# Navigate to DeadlyMusubi
cd ~/workspace/deadlygraphics/DeadlyMusubi

# Create venv with specific configuration
python3 -m venv ~/venvs/[config_name]
source ~/venvs/[config_name]/bin/activate

# Install from requirements file
pip install -r venv_configs/[config_file].txt
```

### Using the Launcher Script

```bash
# Use the DeadlyMusubi launcher (recommended)
./scripts/deadly_launcher.sh --config cuda121_torch25_baseline --project my_training
```

## Configuration File Format

Each `.txt` file contains pip requirements with specific versions:

```
# PyTorch with CUDA version
torch==2.5.1+cu121
torchvision==0.20.1+cu121
torchaudio==2.5.1+cu121

# Core dependencies
numpy==2.3.3
transformers==4.57.3
...
```

## Version Compatibility Matrix

| Configuration | CUDA | PyTorch | VRAM Min | Target GPU |
|--------------|------|---------|----------|------------|
| baseline | 12.1 | 2.5.1 | 16GB | RTX 4080+ |
| fp8_aggressive | 12.1 | 2.5.1 | 12GB | RTX 3060+ |
| legacy | 11.8 | 2.0.1 | 16GB | RTX 3080+ |
| compiled | 12.1 | 2.5.1 | 16GB | RTX 4080+ |

## Testing New Configurations

Before adding a new venv configuration:

1. Test on target hardware
2. Verify CUDA compatibility
3. Run at least 100 training iterations
4. Monitor VRAM usage
5. Check for NaN in loss
6. Document performance metrics

## Common Issues

### CUDA Version Mismatch
If you see "CUDA version mismatch" errors:
- Check NVIDIA driver version: `nvidia-smi`
- Ensure PyTorch CUDA version matches available CUDA
- May need to downgrade/upgrade CUDA toolkit

### Import Errors
If packages won't import:
- Ensure venv is activated
- Check Python version (needs 3.10+)
- Reinstall with `--force-reinstall` flag

### OOM During Installation
If pip runs out of memory:
- Use `--no-cache-dir` flag
- Install packages one at a time
- Increase swap space

## Adding New Configurations

To add a new venv configuration:

1. Create requirements file: `[name].txt`
2. Test thoroughly on target hardware
3. Document in this README
4. Create corresponding knowledge base entry
5. Update compatibility matrix

## Related Documentation

- `/knowledge_base/proven_constants/` - Verified working configs
- `/knowledge_base/variables/` - Experimental configs to try
- `/templates/` - Training script templates
- `/scripts/` - Launcher and utility scripts
