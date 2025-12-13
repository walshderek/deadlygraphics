# Deadly Graphics Roadmap & Task List

This is the living document for the framework's development.

## 🚨 CRITICAL ARCHITECTURE FIXES (Immediate Action)
- [ ] **Repo Sync:** Re-install DG apps from the official \deadlygraphics\ repo.
- [ ] **Directory Migration:** Move the AI stack to \/home/seanf/workspace/deadlygraphics/ai/apps/\.
- [ ] **Model Pathing:** Configure \extra_model_paths.yaml\ to point to \/mnt/c/AI/models/\.

## 🔄 MUSUBI / WAN 2.1 MIGRATION (New)
- [ ] **Install Musubi Tuner:** Clone the Linux-compatible version of Musubi Tuner (Wan branch) into the apps folder.
- [ ] **Path Conversion:** Implement the \path_converter\ script to auto-swap \C:\\AI\ to \/mnt/c/AI\ in all legacy configs.
- [ ] **Template Deployment:** Ensure \wan_train_template.sh\ is deployed to the Musubi folder during setup.
- [ ] **Neutralization:** Ensure TOML generation accepts \[PROJECT_NAME]\ and \[TRIGGER_WORD]\ flags.

## ✅ COMPLETED / VERIFIED
- [x] **ComfyUI Launch:** Verified working on RTX 4080 (Port 8188).
- [x] **AI-Toolkit Launch:** Verified CLI entry point works without CUDA errors.
- [x] **Docs:** Established README, MANIFESTO, ROADMAP, and CONFIGURATION standards.

## 🚨 Immediate Priorities (Grant Deadline)
- [ ] **Grant Application:** Finalize "Innovate UK Creative Catalyst" pitch (Deadline: Jan 2026).
- [ ] **Visual Proof:** Generate 3 "Hero Images" using ComfyUI.
- [ ] **Legal Scaffold:** Draft the "£10 Investor" contract logic.

## 🛠 Technical Framework
- [ ] Refine "Vibecoding" workflow for Unity integration.
- [ ] Train "Deadly Style" LoRA on OneTrainer.
- [ ] Build the "Patron Portal" UI mockup.

## ⚖️ Legal & Financial Framework
- [ ] Define the "Community Benefit Society" (BenCom) structure.
- [ ] Map out the "Revenue Share Agreement" flow.
