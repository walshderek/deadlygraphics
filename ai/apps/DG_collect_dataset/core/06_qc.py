import sys
import os
import shutil
from pathlib import Path

# Force CPU for DeepFace/TensorFlow to avoid JIT/CUDA errors in QC
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3" # Suppress TF logging

import utils

def run(slug):
    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['clean']
    out_dir = path / utils.DIRS['qc']
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🔍 QC Checking faces for {slug}...")
    
    files = [f for f in os.listdir(in_dir) if f.lower().endswith('.jpg')]
    if not files: return

    # Lazy import to apply env vars first
    from deepface import DeepFace
    from sklearn.cluster import DBSCAN
    import numpy as np

    embeddings = []
    valid_files = []

    print(f"   Generating embeddings for {len(files)} images...")
    # 1. Get Embeddings
    for f in files:
        try:
            # Get face embedding
            embedding = DeepFace.represent(
                img_path=str(in_dir / f), 
                model_name="Facenet", 
                enforce_detection=False
            )[0]["embedding"]
            embeddings.append(embedding)
            valid_files.append(f)
        except Exception: 
            pass
    
    if not embeddings: 
        print("   ⚠️ No faces detected for QC. Copying all.")
        for f in files: shutil.copy(in_dir / f, out_dir / f)
        return

    # 2. Cluster
    print("   Clustering faces...")
    # eps=10.0 is loose, fits Facenet euclidean distance
    clustering = DBSCAN(eps=10.0, min_samples=3).fit(embeddings)
    labels = clustering.labels_
    
    # Find majority cluster
    from collections import Counter
    counts = Counter(labels)
    # Ignore noise (-1)
    if -1 in counts: del counts[-1]
    
    if not counts:
        print("   ⚠️ No clear cluster found. Keeping all.")
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
            src_txt = in_dir / txt
            if src_txt.exists():
                shutil.copy(src_txt, out_dir / txt)
            kept += 1
            
    print(f"✅ QC Complete. Kept {kept}/{len(files)} images.")