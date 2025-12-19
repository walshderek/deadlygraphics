# DeadlyMusubi

**DeadlyMusubi** is a specialized branch of Musubi Tuner focused on achieving efficient DualMode Wan 2.2 MOE training on consumer-grade NVIDIA RTX 3000/4000 series GPUs.

## Mission Statement

Enable deployment of MusubiTuner where **DualMode Wan 2.2 MOE training** can successfully complete on a 3000 or 4000 series NVIDIA GPU with a 256x256 imageset training in **less than 4 hours**.

## Performance Targets

- **Training Time**: < 4 hours for 256x256 imageset
- **Iterations per Second**: < 5 it/s
- **Memory**: Avoid OOM (Out of Memory) on consumer GPUs
- **Stability**: Prevent NaN (Not a Number) in learning rate

## Primary Challenges

1. **OOM (Out of Memory)**: VRAM limitations on consumer GPUs
2. **NaN (Not a Number)**: Learning rate instability during training

## Architecture

DeadlyMusubi uses a multi-venv approach to override CUDA, PyTorch, NumPy, and other critical dependencies to find optimal configurations for training stability and performance.

### Directory Structure

```
DeadlyMusubi/
├── venv_configs/        # Virtual environment specifications
├── knowledge_base/      # Configuration classifications
│   ├── proven_constants/    # Verified working configurations
│   ├── disproven_factors/   # Known unsuccessful configurations
│   └── variables/           # Experimental configurations
├── templates/           # Training templates and configs
├── scripts/            # Launcher and utility scripts
└── README.md           # This file
```

## Knowledge Base Classifications

### 1. Proven Constants
Pairings that have **successfully worked** for users in production environments. These configurations are battle-tested and recommended for immediate use.

### 2. Disproven Factors
Factors currently **known to be unsuccessful**, but maintained for historical reference. These may work in future with different hardware or software versions.

### 3. Variables
Experimental configurations that **might or might not work**. These are testable hypotheses awaiting validation.

## Getting Started

### Prerequisites
- NVIDIA RTX 3000 or 4000 series GPU
- Ubuntu/WSL2 Linux environment
- Python 3.10+
- CUDA-compatible drivers

### Quick Start

1. **Choose a venv configuration** from `venv_configs/`
2. **Create and activate the virtual environment**
3. **Run the DeadlyMusubi launcher** with your chosen configuration
4. **Monitor training** for OOM and NaN issues

Detailed instructions are available in each configuration's README.

## Configuration Strategy

DeadlyMusubi tests various combinations of:
- CUDA versions (11.8, 12.1, 12.4)
- PyTorch versions (2.0.x, 2.1.x, 2.5.x)
- NumPy versions
- Memory optimization flags (fp8, bf16, gradient checkpointing)
- Optimizer settings (AdamW8bit, AdamW, SGD)
- Learning rate schedules

## Contributing

When testing configurations:
1. Document all settings thoroughly
2. Record exact hardware specs
3. Note success/failure with timestamps
4. Include error logs for failures
5. Report performance metrics (it/s, VRAM usage, training time)

## Integration with Musubi Tuner

DeadlyMusubi integrates with the standard Musubi Tuner workflow by:
- Using the existing `wan_train_template.sh` as a base
- Providing venv-specific wrapper scripts
- Maintaining compatibility with existing model paths and configurations

## License

Proprietary / TBD (aligned with Deadly Graphics licensing)
