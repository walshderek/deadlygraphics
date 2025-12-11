# Deadly Graphics Architecture

## High-Level Components  
- **DG_vibecoder** — automation engine  
- **Overseer system** — patch generator + manifest manager  
- **GitHub Mirror** — canonical repository state  
- **Docs Suite** — auto-generated & AI-updated  

---

## MARCO (Dump)
Produces a complete snapshot of the DG_vibecoder environment:  
- All files  
- Metadata  
- Structure  
- Instructions for patch insertion  

---

## POLO (Implement)
Reads overseer patches and updates the actual codebase:  
- File rewrites  
- Insert-after ops  
- Replace ops  
- New file creation  

POLO is deterministic and safe.  

---

## Principles  
- No manual editing of core components  
- Overseer is the single source of truth  
- Vibecoder must always remain operable  
- Every update is reversible  

This file will expand automatically as new subsystems are added.