#!/usr/bin/env python3
"""Script de test pour vérifier que tout est bien installé"""
import sys

print("🧪 Test de l'installation...")
print()

try:
    import cv2
    print(f"✅ OpenCV installé : version {cv2.__version__}")
except ImportError:
    print("❌ OpenCV non installé")
    sys.exit(1)

try:
    import numpy as np
    print(f"✅ NumPy installé : version {np.__version__}")
except ImportError:
    print("❌ NumPy non installé")
    sys.exit(1)

# Vérifier que les trackers sont disponibles
try:
    tracker = cv2.TrackerCSRT_create()
    print("✅ Tracker CSRT disponible")
except:
    print("❌ Tracker CSRT non disponible")
    sys.exit(1)

print()
print("🎉 Tout est prêt ! Vous pouvez commencer le tracking.")
