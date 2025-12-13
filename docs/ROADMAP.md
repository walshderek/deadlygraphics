# Deadly Graphics Roadmap & Task List

This is the living document for the framework's development.

## 🚨 CRITICAL ARCHITECTURE FIXES (Immediate Action)
- [ ] **Repo Sync:** Re-install DG apps from the official \deadlygraphics\ repo (currently running generic clones).
- [ ] **Directory Migration:** Move the AI stack from \~/Diamond-Stack\ to the canonical path: 
  \/home/seanf/workspace/deadlygraphics/ai/apps/\.
- [ ] **Model Pathing:** Configure \extra_model_paths.yaml\ (and equivalent for training) to point to the Windows storage: 
  \/mnt/c/AI/models/\ (mapped from \C:\AI\models\).

## 🔄 MUSUBI / WAN 2.2 MIGRATION (New)
- [ ] **Install Musubi Tuner:** Clone the Linux-compatible version of Musubi Tuner into the apps folder.
- [ ] **Path Conversion:** Implement the \path_converter\ script to auto-swap \C:\\AI\ to \/mnt/c/AI\ in all legacy configs.
- [ ] **Template Deployment:** Ensure \wan_train_template.sh\ (Wan 2.2) is deployed to the Musubi folder during setup.
- [ ] **Neutralization:** Ensure TOML generation accepts \[PROJECT_NAME]\ and \[TRIGGER_WORD]\ flags.

## ✅ COMPLETED / VERIFIED
- [x] **ComfyUI Launch:** Verified working on RTX 4080 (Port 8188).
- [x] **AI-Toolkit Launch:** Verified CLI entry point works without CUDA errors.
- [x] **Docs:** Established README, MANIFESTO, ROADMAP, and CONFIGURATION standards.

## 🚨 Immediate Priorities
- [ ] **Visual Proof:** Generate 3 "Hero Images" using ComfyUI (The Patron, The Studio, The Contract).
- [ ] **Legal Scaffold:** Draft the production contract logic using AI for human review.

## 🛠 Technical Framework
- [ ] Refine "Vibecoding" workflow for Unity integration.
- [ ] Train "Deadly Style" LoRA on OneTrainer for consistent film look.
- [ ] Build the "Studio Portal" UI mockup.

## 🧊 Backlog (Future Ideas)
- [ ] AI-driven "dailies" reviewer.
- [ ] Automated asset tracking system.
