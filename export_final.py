#!/usr/bin/env python3
"""
Export avec RATIO FIXE et taille constante
Résout le problème d'images déformées
"""

import cv2
import csv
import sys
import os
import subprocess
import numpy as np


def load_coordinates(csv_path):
    """Charge les coordonnées"""
    coords = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            coords.append((
                int(row['frame']),
                int(row['x']),
                int(row['y']),
                int(row['w']),
                int(row['h'])
            ))
    return coords


def stabilize_and_smooth_coordinates(coords, smooth_window=15):
    """Stabilise et lisse les coordonnées"""
    if len(coords) < smooth_window:
        return coords

    frames = [c[0] for c in coords]
    xs = [c[1] for c in coords]
    ys = [c[2] for c in coords]
    ws = [c[3] for c in coords]
    hs = [c[4] for c in coords]

    # Taille médiane
    median_w = int(np.median(ws))
    median_h = int(np.median(hs))

    print(f"   Stabilizing size to median: {median_w}x{median_h}")

    # Filtre médian pour outliers
    xs_filtered = []
    ys_filtered = []

    for i in range(len(xs)):
        start = max(0, i - smooth_window // 2)
        end = min(len(xs), i + smooth_window // 2 + 1)

        window_xs = xs[start:end]
        window_ys = ys[start:end]

        median_x = np.median(window_xs)
        median_y = np.median(window_ys)

        if abs(xs[i] - median_x) > 200:
            xs_filtered.append(median_x)
        else:
            xs_filtered.append(xs[i])

        if abs(ys[i] - median_y) > 200:
            ys_filtered.append(median_y)
        else:
            ys_filtered.append(ys[i])

    # Lissage
    smoothed = []
    for i in range(len(frames)):
        start = max(0, i - smooth_window // 2)
        end = min(len(frames), i + smooth_window // 2 + 1)

        avg_x = int(np.mean(xs_filtered[start:end]))
        avg_y = int(np.mean(ys_filtered[start:end]))

        smoothed.append((frames[i], avg_x, avg_y, median_w, median_h))

    return smoothed


def calculate_fixed_crop(x, y, w, h, target_w, target_h, video_width, video_height):
    """
    Calcule un crop de taille EXACTE avec le bon ratio
    Centre sur la position (x,y,w,h) mais maintient target_w x target_h
    """
    # Centre de la zone trackée
    center_x = x + w // 2
    center_y = y + h // 2

    # Calculer le crop centré de taille fixe
    crop_x = center_x - target_w // 2
    crop_y = center_y - target_h // 2

    # Ajuster si on sort des limites
    if crop_x < 0:
        crop_x = 0
    if crop_y < 0:
        crop_y = 0
    if crop_x + target_w > video_width:
        crop_x = video_width - target_w
    if crop_y + target_h > video_height:
        crop_y = video_height - target_h

    return crop_x, crop_y, target_w, target_h


def crop_and_export_fixed_ratio(video_path, coords_csv, output_path="output.mov",
                                margin_factor=1.5, smooth_window=15):
    """
    Export avec ratio FIXE - pas de déformation
    """

    if not os.path.exists(video_path):
        print(f"ERROR: Video '{video_path}' not found")
        sys.exit(1)

    if not os.path.exists(coords_csv):
        print(f"ERROR: Coordinates file '{coords_csv}' not found")
        sys.exit(1)

    print(f"Opening video: {video_path}")
    video = cv2.VideoCapture(video_path)

    if not video.isOpened():
        print("ERROR: Cannot open video")
        sys.exit(1)

    # Propriétés
    fps = video.get(cv2.CAP_PROP_FPS)
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    original_ratio = width / height

    print(f"Video properties:")
    print(f"   Resolution: {width}x{height}")
    print(f"   Aspect ratio: {original_ratio:.2f}")
    print(f"   FPS: {fps:.2f}")
    print(f"   Total frames: {total_frames}")
    print()

    # Charger et stabiliser
    print(f"Loading coordinates from '{coords_csv}'...")
    coords = load_coordinates(coords_csv)
    print(f"Loaded {len(coords)} coordinates")
    print()

    print(f"Stabilizing and smoothing (window={smooth_window})...")
    coords = stabilize_and_smooth_coordinates(coords, smooth_window)
    print()

    # Calculer la taille de crop - SIMPLE
    median_w = int(np.median([c[3] for c in coords]))
    median_h = int(np.median([c[4] for c in coords]))

    # Appliquer la marge
    crop_w = int(median_w * margin_factor)
    crop_h = int(median_h * margin_factor)

    # Limiter à la taille de la vidéo
    if crop_w > width:
        crop_w = width
    if crop_h > height:
        crop_h = height

    # Calculer le ratio pour information
    final_ratio = crop_w / crop_h

    print(f"Final crop size: {crop_w}x{crop_h}")
    print(f"Final aspect ratio: {final_ratio:.2f} (original: {original_ratio:.2f})")
    print()

    # Dictionnaire
    coords_dict = {c[0]: c for c in coords}
    first_tracked_frame = min(coords_dict.keys())

    # Position initiale
    first_coord = coords_dict[first_tracked_frame]
    _, x, y, w, h = first_coord
    initial_crop_x, initial_crop_y, _, _ = calculate_fixed_crop(
        x, y, w, h, crop_w, crop_h, width, height
    )

    print(f"First tracked frame: {first_tracked_frame}")
    print()

    # Fichier temporaire
    temp_output = output_path.replace('.mov', '_temp.avi')

    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    out = cv2.VideoWriter(temp_output, fourcc, fps, (crop_w, crop_h))

    if not out.isOpened():
        print("ERROR: Cannot create output file")
        video.release()
        sys.exit(1)

    print("Processing video with FIXED ASPECT RATIO...")
    print()

    video.set(cv2.CAP_PROP_POS_FRAMES, 0)

    frame_count = 0
    processed_count = 0
    last_crop = (initial_crop_x, initial_crop_y, crop_w, crop_h)

    while True:
        ok, frame = video.read()
        if not ok:
            break

        frame_count += 1

        # Position du crop
        if frame_count in coords_dict:
            _, x, y, w, h = coords_dict[frame_count]
            crop_x, crop_y, crop_w_frame, crop_h_frame = calculate_fixed_crop(
                x, y, w, h, crop_w, crop_h, width, height
            )
            last_crop = (crop_x, crop_y, crop_w_frame, crop_h_frame)
        else:
            crop_x, crop_y, crop_w_frame, crop_h_frame = last_crop

        # Crop - TOUJOURS la même taille exacte
        cropped = frame[crop_y:crop_y+crop_h_frame, crop_x:crop_x+crop_w_frame]

        # PAS de resize nécessaire - le crop est déjà à la bonne taille !
        # Mais par sécurité, vérifier quand même
        if cropped.shape[1] != crop_w or cropped.shape[0] != crop_h:
            print(f"Warning at frame {frame_count}: crop size mismatch, resizing")
            cropped = cv2.resize(cropped, (crop_w, crop_h))

        out.write(cropped)
        processed_count += 1

        if frame_count % 30 == 0:
            progress = (frame_count / total_frames) * 100
            print(f"   Progress: {progress:.1f}% ({frame_count}/{total_frames} frames)")

    video.release()
    out.release()

    print()
    print(f"Processed {processed_count} frames")
    print()

    # Ajouter l'audio
    print("Converting to MOV with H.264 and adding audio...")

    cmd = [
        'ffmpeg',
        '-i', temp_output,
        '-i', video_path,
        '-map', '0:v',
        '-map', '1:a',
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '18',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-movflags', '+faststart',
        '-shortest',
        '-y',
        output_path
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print("Audio added successfully!")
        os.remove(temp_output)
    except subprocess.CalledProcessError:
        print("WARNING: Could not add audio")
        print(f"Output file without audio: {temp_output}")

    print()
    print("=" * 50)
    print("Export completed!")
    print("=" * 50)
    print(f"Output file: {output_path}")

    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"File size: {size_mb:.1f} MB")

    print()
    print("Video specs:")
    print(f"   Resolution: {crop_w}x{crop_h}")
    print(f"   Aspect ratio: {final_ratio:.2f}")
    print(f"   NO DISTORTION - Fixed size maintained throughout")

    return True


def main():
    if len(sys.argv) < 3:
        print("Usage: python crop_and_export_fixed_ratio.py <video> <coords.csv> [output.mov] [options]")
        print("\nExample:")
        print("  python crop_and_export_fixed_ratio.py video.mov coords.csv output.mov")
        print("\nOptions:")
        print("  --margin FACTOR    Margin factor (default: 1.5)")
        print("  --smooth WINDOW    Smoothing window (default: 15)")
        sys.exit(1)

    video_path = sys.argv[1]
    coords_csv = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else "output_fixed.mov"

    margin_factor = 1.5
    smooth_window = 15

    i = 4
    while i < len(sys.argv):
        if sys.argv[i] == '--margin' and i + 1 < len(sys.argv):
            margin_factor = float(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--smooth' and i + 1 < len(sys.argv):
            smooth_window = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1

    crop_and_export_fixed_ratio(video_path, coords_csv, output_path,
                                margin_factor, smooth_window)


if __name__ == "__main__":
    main()
