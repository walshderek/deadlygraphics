# Deadly Graphics Roadmap & Task List

This is the living document for the framework's development.

## 🚨 CRITICAL ARCHITECTURE FIXES (Immediate Action)
- [ ] **Repo Sync:** Re-install DG apps from the official \deadlygraphics\ repo (currently running generic clones).
- [ ] **Directory Migration:** Move the AI stack from \~/Diamond-Stack\ to the canonical path: 
  \/home/seanf/workspace/deadlygraphics/ai/apps/\.
- [ ] **Global Environment Config:**
    - [ ] Add \export HF_HOME="/mnt/c/AI/models/huggingface"\ to \.bashrc\.
    - [ ] Create \/mnt/c/AI/models/huggingface\ directory on Windows side.
- [ ] **App Specific Config:**
    - [ ] **AI-Toolkit:** Create \.env\ file with \HF_TOKEN\.
    - [ ] **ComfyUI:** Rename \extra_model_paths.yaml.example\ to \extra_model_paths.yaml\ and set \ase_path: /mnt/c/AI/models\.

## ✅ COMPLETED / VERIFIED
- [x] **ComfyUI Launch:** Verified working on RTX 4080 (Port 8188).
- [x] **AI-Toolkit Launch:** Verified CLI entry point works without CUDA errors.
- [x] **Docs:** Established README, MANIFESTO, ROADMAP, and CONFIGURATION standards.

## 🚨 Immediate Priorities (Grant Deadline)
- [ ] **Grant Application:** Finalize "Innovate UK Creative Catalyst" pitch (Deadline: Jan 2026).
- [ ] **Visual Proof:** Generate 3 "Hero Images" using ComfyUI (The Patron, The Studio, The Contract).
- [ ] **Legal Scaffold:** Draft the "£10 Investor" contract logic using AI for human review.

## 🛠 Technical Framework
- [ ] Refine "Vibecoding" workflow for Unity integration.
- [ ] Train "Deadly Style" LoRA on OneTrainer for consistent film look.
- [ ] Build the "Patron Portal" UI mockup (Where they see their 1p return).

## ⚖️ Legal & Financial Framework
- [ ] Define the "Community Benefit Society" (BenCom) structure.
- [ ] Map out the "Revenue Share Agreement" flow.
- [ ] Identify pro-bono legal partners for the "Ethical Arts Council."

## 🧊 Backlog (Future Ideas)
- [ ] AI-driven "dailies" reviewer.
- [ ] Automated royalty distribution smart contract.
