# Proven Constants

This directory contains **verified working configurations** for DeadlyMusubi training on RTX 3000/4000 series GPUs.

## Configuration Format

Each configuration file should include:

1. **Hardware Specs**: GPU model, VRAM, CPU, RAM
2. **Software Versions**: CUDA, PyTorch, NumPy, etc.
3. **Training Parameters**: Learning rate, batch size, optimizer, etc.
4. **Performance Metrics**: it/s, VRAM usage, total training time
5. **Date Verified**: When this configuration was last confirmed working
6. **User/Source**: Who verified this configuration

## Current Proven Configurations

### Configuration Naming Convention

`[GPU_MODEL]_[CUDA_VERSION]_[PYTORCH_VERSION]_[DATE].yaml`

Example: `RTX4080_CUDA121_TORCH25_2024-12.yaml`

## Usage

1. Review configurations that match your hardware
2. Copy the corresponding venv specification to your environment
3. Follow the setup instructions in the configuration file
4. Report any issues or successes back to the knowledge base

## Adding New Proven Configurations

To add a new proven configuration:

1. Successfully complete at least 3 training runs
2. Document all parameters and results
3. Create a YAML file with complete specifications
4. Submit for review before adding to this directory

## Warning

Even "proven" configurations may fail due to:
- Driver version differences
- System-level dependencies
- Model size variations
- Dataset characteristics

Always monitor your first training run carefully.
