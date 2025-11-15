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


def interpolate_gaps(coords):
    """
    Interpola coordenadas faltantes entre frames trackeados
    Retorna lista completa con todos los frames interpolados
    """
    if len(coords) < 2:
        return coords

    # Detectar gaps
    gaps_found = []
    for i in range(len(coords) - 1):
        gap_size = coords[i+1][0] - coords[i][0] - 1
        if gap_size > 0:
            gaps_found.append((coords[i][0], coords[i+1][0], gap_size))

    if not gaps_found:
        print("   No gaps found - continuous tracking")
        return coords

    print(f"   Found {len(gaps_found)} gaps, interpolating...")
    total_interpolated = sum(g[2] for g in gaps_found)
    print(f"   Total frames to interpolate: {total_interpolated}")

    # Crear lista completa con interpolación
    result = []

    for i in range(len(coords) - 1):
        current_frame, x1, y1, w1, h1 = coords[i]
        next_frame, x2, y2, w2, h2 = coords[i + 1]

        # Agregar frame actual
        result.append((current_frame, x1, y1, w1, h1))

        # Interpolar frames entre current y next
        gap_size = next_frame - current_frame - 1

        if gap_size > 0:
            for j in range(1, gap_size + 1):
                # Interpolación lineal
                ratio = j / (gap_size + 1)
                interp_frame = current_frame + j
                interp_x = int(x1 + (x2 - x1) * ratio)
                interp_y = int(y1 + (y2 - y1) * ratio)
                interp_w = int(w1 + (w2 - w1) * ratio)
                interp_h = int(h1 + (h2 - h1) * ratio)

                result.append((interp_frame, interp_x, interp_y, interp_w, interp_h))

    # Agregar último frame
    result.append(coords[-1])

    print(f"   Interpolation complete: {len(coords)} -> {len(result)} frames")

    return result


def stabilize_and_smooth_coordinates_ema(coords, smooth_window=45):
    """
    Stabilize and smooth coordinates using EMA (Exponential Moving Average)
    Better for YOLO tracking which re-detects every frame
    """
    if len(coords) < 2:
        return coords

    frames = [c[0] for c in coords]
    xs = [c[1] for c in coords]
    ys = [c[2] for c in coords]
    ws = [c[3] for c in coords]
    hs = [c[4] for c in coords]

    print(f"   Applying EMA smoothing (alpha based on window={smooth_window}) to all dimensions...")

    # Calculate alpha from smooth_window
    # alpha = 2 / (window + 1) gives more weight to recent values
    alpha = 2.0 / (smooth_window + 1)
    print(f"   EMA alpha: {alpha:.4f}")

    # First pass: Remove outliers using median filter
    xs_filtered = []
    ys_filtered = []
    ws_filtered = []
    hs_filtered = []

    for i in range(len(xs)):
        start = max(0, i - smooth_window // 2)
        end = min(len(xs), i + smooth_window // 2 + 1)

        window_xs = xs[start:end]
        window_ys = ys[start:end]
        window_ws = ws[start:end]
        window_hs = hs[start:end]

        median_x = np.median(window_xs)
        median_y = np.median(window_ys)
        median_w = np.median(window_ws)
        median_h = np.median(window_hs)

        # Outlier detection for position (X, Y) - threshold 200px
        if abs(xs[i] - median_x) > 200:
            xs_filtered.append(median_x)
        else:
            xs_filtered.append(xs[i])

        if abs(ys[i] - median_y) > 200:
            ys_filtered.append(median_y)
        else:
            ys_filtered.append(ys[i])

        # Outlier detection for size (W, H) - using percentile-based approach
        p75_w = np.percentile(window_ws, 75)
        p75_h = np.percentile(window_hs, 75)

        # If value is more than 50% larger than 75th percentile, use median
        if ws[i] > p75_w * 1.5:
            ws_filtered.append(median_w)
        else:
            ws_filtered.append(ws[i])

        if hs[i] > p75_h * 1.5:
            hs_filtered.append(median_h)
        else:
            hs_filtered.append(hs[i])

    # Second pass: Apply EMA smoothing
    smoothed = []

    # Initialize with first frame (no smoothing)
    ema_x = xs_filtered[0]
    ema_y = ys_filtered[0]
    ema_w = ws_filtered[0]
    ema_h = hs_filtered[0]

    smoothed.append((frames[0], int(ema_x), int(ema_y), int(ema_w), int(ema_h)))

    # Apply EMA for remaining frames
    for i in range(1, len(frames)):
        # EMA formula: new_value = alpha * current + (1 - alpha) * previous_ema
        ema_x = alpha * xs_filtered[i] + (1 - alpha) * ema_x
        ema_y = alpha * ys_filtered[i] + (1 - alpha) * ema_y
        ema_w = alpha * ws_filtered[i] + (1 - alpha) * ema_w
        ema_h = alpha * hs_filtered[i] + (1 - alpha) * ema_h

        smoothed.append((frames[i], int(ema_x), int(ema_y), int(ema_w), int(ema_h)))

    # Report statistics
    min_w = min([s[3] for s in smoothed])
    max_w = max([s[3] for s in smoothed])
    min_h = min([s[4] for s in smoothed])
    max_h = max([s[4] for s in smoothed])

    print(f"   Size range after EMA smoothing: W={min_w}-{max_w}, H={min_h}-{max_h}")

    return smoothed


def stabilize_and_smooth_coordinates(coords, smooth_window=15):
    """Stabilise et lisse les coordonnées avec rolling window pour TOUTES les dimensions"""
    if len(coords) < smooth_window:
        return coords

    frames = [c[0] for c in coords]
    xs = [c[1] for c in coords]
    ys = [c[2] for c in coords]
    ws = [c[3] for c in coords]
    hs = [c[4] for c in coords]

    print(f"   Applying rolling window smoothing (window={smooth_window}) to all dimensions...")

    # Filtre médian pour outliers sur X et Y
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

    # Filtre de outliers sur W et H usando percentiles para evitar spikes extremos
    ws_filtered = []
    hs_filtered = []

    for i in range(len(ws)):
        start = max(0, i - smooth_window // 2)
        end = min(len(ws), i + smooth_window // 2 + 1)

        window_ws = ws[start:end]
        window_hs = hs[start:end]

        # Usar percentil 75 como referencia para detectar outliers extremos
        p75_w = np.percentile(window_ws, 75)
        p75_h = np.percentile(window_hs, 75)
        median_w = np.median(window_ws)
        median_h = np.median(window_hs)

        # Si el valor actual es más del 50% mayor que el percentil 75, usar la mediana
        if ws[i] > p75_w * 1.5:
            ws_filtered.append(median_w)
        else:
            ws_filtered.append(ws[i])

        if hs[i] > p75_h * 1.5:
            hs_filtered.append(median_h)
        else:
            hs_filtered.append(hs[i])

    # Lissage con rolling mean para TODAS las dimensiones
    smoothed = []
    for i in range(len(frames)):
        start = max(0, i - smooth_window // 2)
        end = min(len(frames), i + smooth_window // 2 + 1)

        avg_x = int(np.mean(xs_filtered[start:end]))
        avg_y = int(np.mean(ys_filtered[start:end]))
        avg_w = int(np.mean(ws_filtered[start:end]))
        avg_h = int(np.mean(hs_filtered[start:end]))

        smoothed.append((frames[i], avg_x, avg_y, avg_w, avg_h))

    # Reportar estadísticas
    min_w = min([s[3] for s in smoothed])
    max_w = max([s[3] for s in smoothed])
    min_h = min([s[4] for s in smoothed])
    max_h = max([s[4] for s in smoothed])

    print(f"   Size range after smoothing: W={min_w}-{max_w}, H={min_h}-{max_h}")

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

    print(f"Interpolating missing frames...")
    coords = interpolate_gaps(coords)
    print()

    print(f"Stabilizing and smoothing with EMA (window={smooth_window})...")
    coords = stabilize_and_smooth_coordinates_ema(coords, smooth_window)
    print()

    # Calculer la taille de crop usando percentil para evitar outliers extremos
    # Usamos percentil 75 como base, que representa un tamaño típico-alto
    # sin ser dominado por spikes extremos (que estarían en el 90-100 percentil)
    ws_all = [c[3] for c in coords]
    hs_all = [c[4] for c in coords]

    p75_w = int(np.percentile(ws_all, 75))
    p75_h = int(np.percentile(hs_all, 75))

    print(f"   Size distribution:")
    print(f"      50th percentile (median): {int(np.median(ws_all))}x{int(np.median(hs_all))}")
    print(f"      75th percentile: {p75_w}x{p75_h}")
    print(f"      90th percentile: {int(np.percentile(ws_all, 90))}x{int(np.percentile(hs_all, 90))}")
    print(f"   Using 75th percentile as base for crop size")

    # Appliquer la marge
    crop_w = int(p75_w * margin_factor)
    crop_h = int(p75_h * margin_factor)

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

    # Buscar FFmpeg en la ubicación local primero
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ffmpeg_local = os.path.join(script_dir, 'ffmpeg', 'bin', 'ffmpeg.exe')

    if os.path.exists(ffmpeg_local):
        ffmpeg_cmd = ffmpeg_local
        print(f"   Using local FFmpeg: {ffmpeg_cmd}")
    else:
        ffmpeg_cmd = 'ffmpeg'
        print("   Using system FFmpeg")

    cmd = [
        ffmpeg_cmd,
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
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Audio added successfully!")
        os.remove(temp_output)
    except FileNotFoundError:
        print("ERROR: FFmpeg not found!")
        print(f"Tried: {ffmpeg_cmd}")
        print("Output file WITHOUT audio saved as: {temp_output}")
        print("\nPlease install FFmpeg or ensure it's in the correct location.")
        return False
    except subprocess.CalledProcessError as e:
        print("WARNING: Could not add audio")
        print(f"FFmpeg error: {e.stderr}")
        print(f"Output file without audio: {temp_output}")
        return False

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
