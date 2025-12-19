# OOM (Out of Memory) Mitigation Strategies

## Understanding OOM in Wan 2.2 Training

Out of Memory errors occur when the training process requests more VRAM than available on your GPU. Wan 2.2 is a large model (14B parameters) that requires careful memory management on consumer GPUs.

## Quick Reference

| GPU Model | VRAM | Minimum Settings | Recommended Settings |
|-----------|------|------------------|---------------------|
| RTX 3060 | 12GB | fp8 + AdamW8bit + grad_checkpoint | fp8 + AdamW8bit + grad_checkpoint + batch_size=1 |
| RTX 3070 | 8GB | Not recommended | Consider RTX 3060 or better |
| RTX 3080 | 10GB | fp8 + AdamW8bit + grad_checkpoint | fp8 + AdamW8bit + grad_checkpoint + reduced resolution |
| RTX 4080 | 16GB | fp8 + AdamW8bit | fp8 + AdamW8bit + grad_checkpoint |
| RTX 4090 | 24GB | fp16 + AdamW | fp8 + AdamW (for safety margin) |

## Memory Optimization Techniques (Ordered by Impact)

### 1. Precision Reduction (Saves 60-70% VRAM)

**Most Aggressive - fp8:**
```bash
--fp8_base --fp8_scaled --fp8_t5
```
- Reduces model weights to 8-bit floating point
- Minimal quality impact for LoRA training
- **Recommended for all 12-16GB GPUs**

**Moderate - bf16:**
```bash
--bf16
```
- Better quality than fp8, higher memory usage
- Requires CUDA 12.1+ and Ampere+ GPUs
- **Recommended for 20GB+ GPUs**

**Mixed Precision - fp16:**
```bash
--mixed_precision fp16
```
- Automatic mixed precision training
- Good balance of speed and memory
- **Compatible with all modern GPUs**

### 2. Optimizer Optimization (Saves 30-40% VRAM)

**8-bit Optimizer:**
```bash
--optimizer_type AdamW8bit
```
- Uses bitsandbytes quantized optimizer
- Nearly identical results to full AdamW
- **Required for 12GB GPUs**

**Standard Optimizer:**
```bash
--optimizer_type AdamW
```
- Full precision optimizer states
- Only for 20GB+ GPUs

### 3. Gradient Checkpointing (Saves 20-30% VRAM)

```bash
--gradient_checkpointing
```
- Trades compute for memory
- Recomputes activations during backward pass
- ~10-15% slower but essential for small VRAM
- **Recommended for all GPUs under 20GB**

### 4. Batch Size and Accumulation (Variable savings)

**Small batch with accumulation:**
```bash
--train_batch_size 1
--gradient_accumulation_steps 4
```
- Effective batch size = 1 × 4 = 4
- Linear memory scaling with batch size
- **Always start with batch_size=1**

**Larger batch (only for high VRAM):**
```bash
--train_batch_size 2
--gradient_accumulation_steps 2
```
- Requires 20GB+ VRAM for Wan 2.2

### 5. Resolution and Sequence Length (Variable savings)

**Reduce resolution:**
```bash
# In your dataset TOML file
width = 224
height = 224
# Instead of 256x256
```
- VRAM usage scales quadratically with resolution
- 224x224 uses ~25% less VRAM than 256x256

**Reduce frames:**
```bash
# In your dataset TOML file
num_frames = 16
# Instead of 24
```
- For video training, fewer frames = less VRAM

## Recommended Configurations by GPU

### RTX 3060 (12GB) - Tight Budget
```bash
accelerate launch wan_train_network.py \
    --fp8_base --fp8_scaled --fp8_t5 \
    --optimizer_type AdamW8bit \
    --gradient_checkpointing \
    --train_batch_size 1 \
    --gradient_accumulation_steps 4 \
    --mixed_precision fp16 \
    [other args...]
```

### RTX 4080 (16GB) - Comfortable
```bash
accelerate launch wan_train_network.py \
    --fp8_base --fp8_scaled --fp8_t5 \
    --optimizer_type AdamW8bit \
    --gradient_checkpointing \
    --train_batch_size 1 \
    --gradient_accumulation_steps 4 \
    [other args...]
```

### RTX 4090 (24GB) - Optimal
```bash
accelerate launch wan_train_network.py \
    --bf16 \
    --optimizer_type AdamW \
    --train_batch_size 1 \
    --gradient_accumulation_steps 8 \
    [other args...]
```

## Troubleshooting OOM

### If you get OOM during model loading:
1. Enable fp8 for all components
2. Close all other GPU applications
3. Restart system to clear GPU memory

### If you get OOM during forward pass:
1. Reduce batch size to 1
2. Enable gradient checkpointing
3. Reduce resolution or sequence length

### If you get OOM during backward pass:
1. Reduce gradient accumulation steps
2. Enable CPU offload (if desperate)

### If you get OOM during optimizer step:
1. Switch to AdamW8bit
2. Enable optimizer CPU offload

## Monitoring VRAM Usage

```bash
# Watch VRAM in real-time
watch -n 1 nvidia-smi

# Log VRAM usage during training
nvidia-smi --query-gpu=timestamp,memory.used,memory.free \
    --format=csv -l 1 > vram_log.csv
```

## Summary: Start Here

For most users, start with this configuration and adjust as needed:

```bash
--fp8_base --fp8_scaled --fp8_t5 \
--optimizer_type AdamW8bit \
--gradient_checkpointing \
--train_batch_size 1 \
--gradient_accumulation_steps 4
```

This should work on any RTX 3060 or better GPU.
