#!/usr/bin/env python3
"""
Analyse les coordonnées de tracking pour détecter les problèmes
"""

import csv
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Backend sans GUI
import matplotlib.pyplot as plt


def analyze_tracking(coords_csv):
    """Analyse le fichier de coordonnées"""

    print(f"Analyzing: {coords_csv}")
    print()

    frames = []
    xs = []
    ys = []
    ws = []
    hs = []

    with open(coords_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            frames.append(int(row['frame']))
            xs.append(int(row['x']))
            ys.append(int(row['y']))
            ws.append(int(row['w']))
            hs.append(int(row['h']))

    print(f"Total frames tracked: {len(frames)}")
    print(f"Frame range: {min(frames)} to {max(frames)}")
    print()

    # Statistiques sur la taille
    print("Bounding box WIDTH statistics:")
    print(f"  Min: {min(ws)}")
    print(f"  Max: {max(ws)}")
    print(f"  Mean: {np.mean(ws):.1f}")
    print(f"  Median: {np.median(ws):.1f}")
    print(f"  Std dev: {np.std(ws):.1f}")
    print()

    print("Bounding box HEIGHT statistics:")
    print(f"  Min: {min(hs)}")
    print(f"  Max: {max(hs)}")
    print(f"  Mean: {np.mean(hs):.1f}")
    print(f"  Median: {np.median(hs):.1f}")
    print(f"  Std dev: {np.std(hs):.1f}")
    print()

    # Détecter les sauts brusques
    jumps = []
    for i in range(1, len(frames)):
        dx = abs(xs[i] - xs[i-1])
        dy = abs(ys[i] - ys[i-1])
        dw = abs(ws[i] - ws[i-1])
        dh = abs(hs[i] - hs[i-1])

        if dx > 100 or dy > 100 or dw > 200 or dh > 200:
            jumps.append((frames[i], dx, dy, dw, dh))

    if jumps:
        print(f"WARNING: {len(jumps)} large jumps detected!")
        print("First 5 jumps:")
        for frame, dx, dy, dw, dh in jumps[:5]:
            print(f"  Frame {frame}: dx={dx}, dy={dy}, dw={dw}, dh={dh}")
        print()

    # Créer des graphiques
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))

    # Position X, Y
    axes[0].plot(frames, xs, label='X position', alpha=0.7)
    axes[0].plot(frames, ys, label='Y position', alpha=0.7)
    axes[0].set_ylabel('Position (pixels)')
    axes[0].set_title('Tracking Position Over Time')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Largeur et hauteur
    axes[1].plot(frames, ws, label='Width', alpha=0.7)
    axes[1].plot(frames, hs, label='Height', alpha=0.7)
    axes[1].axhline(np.median(ws), color='blue', linestyle='--', alpha=0.5, label='Median Width')
    axes[1].axhline(np.median(hs), color='orange', linestyle='--', alpha=0.5, label='Median Height')
    axes[1].set_ylabel('Size (pixels)')
    axes[1].set_title('Bounding Box Size Over Time')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # Ratio (devrait être relativement constant)
    ratios = [w/h for w, h in zip(ws, hs)]
    axes[2].plot(frames, ratios, alpha=0.7)
    axes[2].axhline(np.median(ratios), color='red', linestyle='--', alpha=0.5, label='Median Ratio')
    axes[2].set_ylabel('Width/Height Ratio')
    axes[2].set_xlabel('Frame')
    axes[2].set_title('Aspect Ratio Over Time')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    output_file = coords_csv.replace('.csv', '_analysis.png')
    plt.savefig(output_file, dpi=150)
    print(f"Analysis plot saved to: {output_file}")

    # Recommandations
    print()
    print("=" * 60)
    print("RECOMMENDATIONS:")
    print("=" * 60)

    size_variation = (max(ws) - min(ws)) / np.median(ws) * 100

    if size_variation > 50:
        print("WARNING: Tracking size varies by more than 50%!")
        print("  -> The tracker likely lost the dancers at some point")
        print("  -> Recommendation: Re-track with better settings")
        print()
        print("Suggested improvements:")
        print("  1. Start tracking when BOTH dancers are clearly visible")
        print("  2. Select a larger initial rectangle")
        print("  3. Use --start-time to skip the single dancer part")
    else:
        print("Tracking size variation is acceptable")

    print()
    print(f"Recommended fixed crop size:")
    print(f"  Width: {int(np.median(ws))}")
    print(f"  Height: {int(np.median(hs))}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_tracking.py coords.csv")
        sys.exit(1)

    analyze_tracking(sys.argv[1])
