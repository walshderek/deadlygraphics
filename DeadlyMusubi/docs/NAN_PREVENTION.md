# NaN (Not a Number) Prevention Strategies

## Understanding NaN in Training

NaN (Not a Number) in the loss or gradients is a critical failure that stops training. It occurs when numerical operations produce invalid results, often due to numerical instability.

## Common Causes of NaN

1. **Learning rate too high** - Most common cause
2. **No warmup period** - Sudden large updates
3. **Gradient explosion** - Unstable gradients
4. **Mixed precision issues** - Precision underflow/overflow
5. **Corrupted data** - Invalid inputs in dataset
6. **Division by zero** - Batch normalization with small batches

## Quick Fix Checklist

When you encounter NaN:

- [ ] Reduce learning rate by 10x
- [ ] Add/increase warmup steps (100-500)
- [ ] Enable gradient clipping
- [ ] Check dataset for corrupted samples
- [ ] Verify precision settings
- [ ] Reduce batch size to 1
- [ ] Try different optimizer

## Prevention Strategies (Ordered by Importance)

### 1. Safe Learning Rate (Critical)

**Conservative starting point:**
```bash
--learning_rate 0.0001
```

**Learning rate ranges by model size:**
- Small models (< 1B): 0.0001 - 0.001
- Medium models (1-10B): 0.00005 - 0.0001
- Large models (10B+): 0.00001 - 0.00005

**For Wan 2.2 (14B parameters):**
```bash
--learning_rate 0.0001  # Safe default
--learning_rate 0.00005  # More conservative
--learning_rate 0.00001  # Very safe, slower convergence
```

### 2. Warmup Steps (Essential)

Warmup gradually increases learning rate from 0 to target:

```bash
--warmup_steps 100  # Minimum
--warmup_steps 500  # Recommended
--warmup_steps 1000  # Very conservative
```

### 3. Gradient Clipping (Highly Recommended)

Prevents gradient explosion:

```bash
--max_grad_norm 1.0  # Standard
--max_grad_norm 0.5  # More aggressive
```

### 4. Stable Precision Settings

**Recommended for stability:**
```bash
--fp8_base --fp8_scaled --fp8_t5
--mixed_precision fp16
```

### 5. Optimizer Selection

**Most stable (recommended):**
```bash
--optimizer_type AdamW8bit
--learning_rate 0.0001
```

## Recommended Configuration for Wan 2.2

**Maximum stability configuration:**
```bash
accelerate launch wan_train_network.py \
    --fp8_base --fp8_scaled --fp8_t5 \
    --optimizer_type AdamW8bit \
    --learning_rate 0.00005 \
    --warmup_steps 500 \
    --max_grad_norm 1.0 \
    --train_batch_size 1 \
    --gradient_accumulation_steps 4 \
    --mixed_precision fp16 \
    [other args...]
```

**Balanced configuration:**
```bash
accelerate launch wan_train_network.py \
    --fp8_base --fp8_scaled --fp8_t5 \
    --optimizer_type AdamW8bit \
    --learning_rate 0.0001 \
    --warmup_steps 100 \
    --max_grad_norm 1.0 \
    --train_batch_size 1 \
    --gradient_accumulation_steps 4 \
    [other args...]
```

## Summary: Safe Starting Configuration

Start with these settings for maximum stability:

```bash
--learning_rate 0.0001
--warmup_steps 500
--max_grad_norm 1.0
--optimizer_type AdamW8bit
--lr_scheduler constant_with_warmup
```

Gradually increase learning rate if training is stable.
