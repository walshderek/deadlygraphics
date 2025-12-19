# Disproven Factors

This directory contains **known unsuccessful configurations** that have been tested and found to fail on RTX 3000/4000 series GPUs.

## Purpose

Maintaining a record of failed configurations helps:
- Avoid repeating known failures
- Track patterns in what doesn't work
- Identify potential areas for future improvement
- Save time and resources for the community

## Configuration Format

Each disproven configuration should include:

1. **Hardware Specs**: GPU model, VRAM, CPU, RAM
2. **Software Versions**: CUDA, PyTorch, NumPy, etc.
3. **Attempted Parameters**: What settings were tried
4. **Failure Type**: OOM, NaN, crash, etc.
5. **Error Messages**: Exact error text
6. **Date Tested**: When this was tested
7. **Future Potential**: Why this might work later (optional)

## Common Failure Patterns

### OOM Failures
- CUDA 12.4 + PyTorch 2.5 + batch_size > 1
- Full precision (fp32) on models > 10B parameters
- Insufficient gradient checkpointing

### NaN Failures
- Learning rates > 0.001 with AdamW
- Missing warmup steps
- bf16 on unsupported CUDA versions
- Certain optimizer combinations

### Compatibility Failures
- CUDA version mismatches
- PyTorch built for wrong CUDA version
- NumPy version conflicts

## Naming Convention

`[GPU_MODEL]_[FAILURE_TYPE]_[CUDA_VERSION]_[PYTORCH_VERSION]_[DATE].yaml`

Example: `RTX3060_OOM_CUDA124_TORCH25_2024-12.yaml`

## Re-testing

Configurations in this directory should be periodically re-tested:
- After major NVIDIA driver updates
- After PyTorch/CUDA releases
- After hardware upgrades
- When new optimization techniques emerge

## Adding Disproven Factors

To document a failed configuration:

1. Reproduce the failure at least twice
2. Collect complete error logs
3. Document exact steps to reproduce
4. Create a YAML file with all details
5. Add to this directory with clear failure description

## Note on "Fractional Chance"

Some configurations here have a **fractional chance of working in the future** due to:
- Pending software updates
- Driver improvements
- Better optimization algorithms
- Hardware revisions

These are marked with `future_potential: true` in their YAML files.
