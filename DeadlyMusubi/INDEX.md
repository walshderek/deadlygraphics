# DeadlyMusubi Index

Complete reference guide for the DeadlyMusubi framework.

## 📁 Directory Structure

```
DeadlyMusubi/
├── README.md                    # Main overview and architecture
├── QUICKSTART.md               # 10-minute quick start guide
├── INDEX.md                    # This file - complete reference
├── docs/                       # Technical documentation
│   ├── OOM_MITIGATION.md      # Out of Memory prevention
│   └── NAN_PREVENTION.md      # NaN handling strategies
├── knowledge_base/             # Configuration repository
│   ├── proven_constants/      # Verified working configs
│   ├── disproven_factors/     # Known failures
│   └── variables/             # Experimental configs
├── venv_configs/              # Virtual environment specs
├── scripts/                   # Automation scripts
└── templates/                 # Training templates
```

## 🚀 Quick Navigation

### Getting Started
- **New to DeadlyMusubi?** → [QUICKSTART.md](QUICKSTART.md)
- **Understanding the system** → [README.md](README.md)
- **Installation help** → [venv_configs/README.md](venv_configs/README.md)

### Troubleshooting
- **Out of Memory errors** → [docs/OOM_MITIGATION.md](docs/OOM_MITIGATION.md)
- **NaN in training** → [docs/NAN_PREVENTION.md](docs/NAN_PREVENTION.md)
- **Performance issues** → Knowledge base examples

### Configuration Selection
- **RTX 3060 (12GB)** → [knowledge_base/proven_constants/](knowledge_base/proven_constants/)
- **RTX 4080 (16GB)** → [venv_configs/cuda121_torch25_baseline.txt](venv_configs/cuda121_torch25_baseline.txt)
- **RTX 4090 (24GB)** → [knowledge_base/variables/LOW_RTX4090_extreme_performance.yaml](knowledge_base/variables/LOW_RTX4090_extreme_performance.yaml)

## 📚 Documentation Files

### Core Documentation
| File | Purpose | Audience |
|------|---------|----------|
| [README.md](README.md) | System overview, architecture, mission | Everyone |
| [QUICKSTART.md](QUICKSTART.md) | Fast setup guide | New users |
| [INDEX.md](INDEX.md) | Complete reference (this file) | All users |

### Technical Guides
| File | Purpose | When to Use |
|------|---------|-------------|
| [docs/OOM_MITIGATION.md](docs/OOM_MITIGATION.md) | Memory optimization strategies | Getting OOM errors |
| [docs/NAN_PREVENTION.md](docs/NAN_PREVENTION.md) | Learning rate stability | Getting NaN in loss |

### Knowledge Base READMEs
| File | Purpose |
|------|---------|
| [knowledge_base/proven_constants/README.md](knowledge_base/proven_constants/README.md) | How to use verified configs |
| [knowledge_base/disproven_factors/README.md](knowledge_base/disproven_factors/README.md) | Understanding failures |
| [knowledge_base/variables/README.md](knowledge_base/variables/README.md) | Experimental testing guide |
| [venv_configs/README.md](venv_configs/README.md) | Virtual environment setup |

## 🗂 Configuration Files

### Proven Constants (Verified Working)
1. **RTX4080_CUDA121_TORCH25_baseline.yaml**
   - GPU: RTX 4080 (16GB)
   - Performance: 4.2 it/s, 3.5 hours
   - Resolution: 256x256, 24 frames
   - Status: ✅ Highly reliable

2. **RTX3060Ti_CUDA121_TORCH25_8GB.yaml**
   - GPU: RTX 3060 Ti (8GB)
   - Performance: 5.2 it/s, 4.0 hours
   - Resolution: 224x224, 16 frames (reduced)
   - Status: ✅ Minimum viable config

### Disproven Factors (Known Failures)
1. **RTX3060_OOM_CUDA124_fp32_2024-12.yaml**
   - Issue: OOM with full precision on 12GB
   - Lesson: fp8 required for 12GB GPUs
   - Future potential: Possible with software updates

### Variables (Experimental)
1. **HIGH_RTX4080_fp8_compile_optimization.yaml**
   - Priority: HIGH
   - Goal: 30-50% speedup with torch.compile
   - Risk: Medium
   - Potential: 2.5 hour training

2. **MEDIUM_RTX3060_xformers_memory_optimization.yaml**
   - Priority: MEDIUM
   - Goal: 10-15% VRAM reduction
   - Risk: Low
   - Potential: 256x256 on 12GB cards

3. **LOW_RTX4090_extreme_performance.yaml**
   - Priority: LOW
   - Goal: Sub-2 hour training
   - Risk: High
   - Potential: Research/benchmarking

## 🛠 Virtual Environment Configurations

### Available Configs
| Config File | Target GPU | VRAM | CUDA | PyTorch | Status |
|-------------|-----------|------|------|---------|--------|
| cuda121_torch25_baseline.txt | RTX 4080+ | 16GB+ | 12.1 | 2.5.1 | ✅ Proven |
| cuda121_torch25_fp8_aggressive.txt | RTX 3060+ | 12GB+ | 12.1 | 2.5.1 | 🔬 Variable |
| cuda118_torch20_legacy.txt | RTX 3080 | 16GB | 11.8 | 2.0.1 | ✅ Proven |

### Selection Guide
```
Your GPU → Recommended Config
├─ RTX 3060 (12GB) → cuda121_torch25_fp8_aggressive
├─ RTX 3070 (8GB)  → Not recommended (upgrade needed)
├─ RTX 3080 (10GB) → cuda121_torch25_fp8_aggressive
├─ RTX 4080 (16GB) → cuda121_torch25_baseline
└─ RTX 4090 (24GB) → cuda121_torch25_baseline
```

## 🔧 Scripts and Templates

### Scripts
| File | Purpose | Usage |
|------|---------|-------|
| [scripts/deadly_launcher.sh](scripts/deadly_launcher.sh) | Automated venv launcher | `./deadly_launcher.sh --config baseline` |

### Templates
| File | Purpose | Usage |
|------|---------|-------|
| [templates/deadly_wan_train.sh](templates/deadly_wan_train.sh) | Training script with safety checks | `./deadly_wan_train.sh project_name trigger` |

## 📊 Performance Targets

### Goal Metrics
- ✅ Training time: < 4 hours (256x256 imageset)
- ✅ Iterations/sec: < 5 it/s
- ✅ VRAM: No OOM on target GPU
- ✅ Stability: No NaN in learning rate

### Current Results
| GPU | Config | Resolution | Time | it/s | VRAM Peak |
|-----|--------|-----------|------|------|-----------|
| RTX 3060 Ti (8GB) | fp8_aggressive | 224x224 | 4.0h | 5.2 | 7.8GB |
| RTX 4080 (16GB) | baseline | 256x256 | 3.5h | 4.2 | 14.5GB |
| RTX 4090 (24GB) | baseline | 256x256 | 2.5h | 3.0 | ~18GB |

## 🎯 Common Use Cases

### "I just want it to work"
1. Read [QUICKSTART.md](QUICKSTART.md)
2. Use baseline config for your GPU
3. Follow the proven constant example

### "I'm getting OOM errors"
1. Read [docs/OOM_MITIGATION.md](docs/OOM_MITIGATION.md)
2. Switch to fp8_aggressive config
3. Check disproven factors for similar issues

### "I'm getting NaN in training"
1. Read [docs/NAN_PREVENTION.md](docs/NAN_PREVENTION.md)
2. Reduce learning rate
3. Increase warmup steps

### "I want maximum performance"
1. Check variables for experimental configs
2. Review HIGH priority experiments
3. Test incrementally

### "I want to contribute"
1. Test a variable configuration
2. Document results thoroughly
3. Submit to proven_constants or disproven_factors

## 📈 Knowledge Base Workflow

```
New Configuration Idea
         ↓
  Add to Variables/
         ↓
    Community Testing
         ↓
    ┌────┴────┐
    ↓         ↓
 Success?   Failure?
    ↓         ↓
Proven/   Disproven/
```

## 🔍 File Naming Conventions

### Configuration Files (YAML)
```
[GPU_MODEL]_[CUDA_VERSION]_[PYTORCH_VERSION]_[DESCRIPTOR].yaml

Examples:
- RTX4080_CUDA121_TORCH25_baseline.yaml
- RTX3060_OOM_CUDA124_fp32_2024-12.yaml
```

### Virtual Environment Files (TXT)
```
cuda[VERSION]_torch[VERSION]_[DESCRIPTOR].txt

Examples:
- cuda121_torch25_baseline.txt
- cuda121_torch25_fp8_aggressive.txt
```

### Variable Configurations (YAML)
```
[PRIORITY]_[GPU_TARGET]_[DESCRIPTION].yaml

Examples:
- HIGH_RTX4080_fp8_compile_optimization.yaml
- MEDIUM_RTX3060_xformers_memory_optimization.yaml
```

## 🧪 Testing Checklist

Before adding a configuration to proven_constants:

- [ ] Successfully completed 3+ training runs
- [ ] Documented all hardware specs
- [ ] Measured VRAM usage
- [ ] Recorded training time
- [ ] Verified no OOM errors
- [ ] Verified no NaN in loss
- [ ] Confirmed reproducibility
- [ ] Checked output quality

## 📖 Additional Resources

### Within DeadlyMusubi
- All READMEs contain detailed usage instructions
- YAML files include complete configuration specs
- Scripts have inline documentation

### External References
- Musubi Tuner documentation
- PyTorch optimization guides
- NVIDIA CUDA documentation

## 🤝 Contributing

### Adding Proven Constants
1. Test configuration thoroughly (3+ runs)
2. Create YAML with complete specs
3. Include performance metrics
4. Document any caveats

### Adding Disproven Factors
1. Reproduce failure consistently (3+ times)
2. Document exact error messages
3. Explain root cause
4. Suggest what might work instead

### Adding Variables
1. Research the hypothesis
2. Document expected benefits and risks
3. Assign appropriate priority
4. Provide testing methodology

## 📝 Version Information

- **Framework Version**: 1.0
- **Last Updated**: 2024-12-19
- **Total Configurations**: 6 (2 proven, 1 disproven, 3 variables)
- **Total Documentation**: ~1300+ lines
- **Supported GPUs**: RTX 3000/4000 series

## 🆘 Getting Help

1. **Check documentation first** (this index)
2. **Review similar configurations** (knowledge base)
3. **Read error logs carefully**
4. **Document your issue completely**
5. **Share your configuration and results**

## 🎓 Understanding DeadlyMusubi

The framework is designed around three key principles:

1. **Classification**: Separate what works, what doesn't, and what's unknown
2. **Documentation**: Complete specs for reproducibility
3. **Community**: Share knowledge to avoid repeated failures

Every configuration tells a story:
- **Proven Constants**: "This worked for me"
- **Disproven Factors**: "This failed because..."
- **Variables**: "This might work if..."

---

**Welcome to DeadlyMusubi!** 🚀

The goal is simple: Make Wan 2.2 training accessible on consumer GPUs by documenting what works, what doesn't, and what might work in the future.
