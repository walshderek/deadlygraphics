# Variables

This directory contains **experimental configurations** that might or might not work. These are untested hypotheses awaiting validation.

## Purpose

The variables directory serves as:
- A testing queue for new configurations
- A hypothesis bank for community experiments
- A brainstorming space for optimization ideas
- A staging area before promotion to proven/disproven

## Configuration Format

Each variable configuration should include:

1. **Hypothesis**: What we think might work and why
2. **Hardware Target**: Intended GPU models
3. **Software Versions**: Proposed CUDA, PyTorch, NumPy, etc.
4. **Expected Benefits**: Why this might improve performance
5. **Potential Risks**: What could go wrong
6. **Test Priority**: High/Medium/Low
7. **Date Added**: When this was proposed
8. **Proposer**: Who suggested this configuration

## Testing Workflow

1. **Propose**: Add new variable configuration
2. **Review**: Community reviews for feasibility
3. **Test**: Volunteers test the configuration
4. **Document**: Record results thoroughly
5. **Promote**: Move to proven_constants or disproven_factors

## Priority Levels

### High Priority
Configurations likely to work based on:
- Similar proven configurations
- Official documentation support
- Community reports from other projects

### Medium Priority
Configurations with mixed evidence:
- Some theoretical support
- Unverified community reports
- Partial compatibility

### Low Priority
Experimental configurations:
- Purely theoretical
- Limited documentation
- High risk of failure
- Long-shot optimizations

## Naming Convention

`[PRIORITY]_[GPU_TARGET]_[HYPOTHESIS_BRIEF]_[DATE].yaml`

Example: `HIGH_RTX4080_fp8_aggressive_2024-12.yaml`

## Current Research Areas

### Memory Optimization
- Gradient checkpointing strategies
- fp8 vs bf16 vs fp16 precision mixes
- Model parallelism approaches
- Attention optimization methods

### Learning Rate Stability
- Warmup schedules
- Optimizer variants
- Loss scaling techniques
- Gradient clipping strategies

### Performance Improvements
- CUDA graph optimizations
- Batch size experiments
- Compile-mode PyTorch
- XFormers integration

## Contributing Variables

To propose a new variable configuration:

1. Research the hypothesis thoroughly
2. Check it's not already proven/disproven
3. Document expected outcomes
4. Provide testing methodology
5. Submit with clear rationale

## Graduation Criteria

### To Proven Constants
- Successfully complete 3+ independent training runs
- Achieve performance targets (< 4hrs, < 5 it/s)
- No OOM or NaN failures
- Reproducible by at least 2 different users

### To Disproven Factors
- Fail consistently across 3+ attempts
- Clear, reproducible failure mode
- Multiple users confirm failure
- Technical explanation for why it fails

## Active Experiments

Document ongoing experiments here with:
- Current status
- Preliminary results
- Next steps
- Contact for collaboration
