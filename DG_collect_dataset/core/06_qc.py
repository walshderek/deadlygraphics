import sys
import os
import utils
import shutil
from deepface import DeepFace
from sklearn.cluster import DBSCAN
import numpy as np

def run(slug):
    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['clean']
    out_dir = path / utils.DIRS['qc']
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🔍 QC Checking faces for {slug}...")
    
    files = [f for f in os.listdir(in_dir) if f.lower().endswith('.jpg')]
    if not files: return

    embeddings = []
    valid_files = []

    # 1. Get Embeddings
    for f in files:
        try:
            # Get face embedding
            embedding = DeepFace.represent(img_path=str(in_dir / f), model_name="Facenet", enforce_detection=False)[0]["embedding"]
            embeddings.append(embedding)
            valid_files.append(f)
        except: pass
    
    if not embeddings: return

    # 2. Cluster
    # eps=0.5 is typical for Facenet cosine distance
    clustering = DBSCAN(eps=10.0, min_samples=3).fit(embeddings)
    labels = clustering.labels_
    
    # Find majority cluster
    from collections import Counter
    counts = Counter(labels)
    # Ignore noise (-1)
    if -1 in counts: del counts[-1]
    
    if not counts:
        print("⚠️ No clear cluster found. Keeping all.")
        majority_label = -1
    else:
        majority_label = counts.most_common(1)[0][0]
        
    print(f"   Majority Cluster: {majority_label} (Size: {counts[majority_label]})")

    # 3. Filter
    kept = 0
    for f, label in zip(valid_files, labels):
        if label == majority_label or majority_label == -1:
            shutil.copy(in_dir / f, out_dir / f)
            # Copy caption
            txt = os.path.splitext(f)[0] + ".txt"
            if (in_dir / txt).exists():
                shutil.copy(in_dir / txt, out_dir / txt)
            kept += 1
            
    print(f"✅ QC Complete. Kept {kept}/{len(files)} images.")