#!/usr/bin/env python3
"""
Tracking amélioré avec détection des problèmes et visualisation
"""

import cv2
import csv
import sys
import os
from pathlib import Path


def select_and_track_improved(video_path, output_csv="coords.csv", start_time=0, tracker_type="CSRT"):
    """
    Tracking amélioré avec:
    - Détection de perte de tracking
    - Visualisation du problème
    - Possibilité de réinitialiser (touche R)
    - Choix du tracker
    """

    if not os.path.exists(video_path):
        print(f"ERROR: Video '{video_path}' not found")
        sys.exit(1)

    print(f"Opening video: {video_path}")
    video = cv2.VideoCapture(video_path)

    if not video.isOpened():
        print("ERROR: Cannot open video")
        sys.exit(1)

    # Lire la première image
    ok, frame = video.read()
    if not ok:
        print("ERROR: Cannot read first frame")
        sys.exit(1)

    # Propriétés vidéo
    fps = video.get(cv2.CAP_PROP_FPS)
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"Video properties:")
    print(f"   Resolution: {width}x{height}")
    print(f"   FPS: {fps:.2f}")
    print(f"   Total frames: {total_frames}")
    print(f"   Duration: {total_frames/fps:.1f} seconds")
    print()

    # Si start_time spécifié, aller à cette position
    start_frame = 0
    if start_time > 0:
        start_frame = int(start_time * fps)
        print(f"Starting from {start_time} seconds (frame {start_frame})")
        video.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        ok, frame = video.read()
        if not ok:
            print("ERROR: Cannot read frame at specified start time")
            sys.exit(1)
        print()

    # Sélection manuelle
    print("INSTRUCTIONS:")
    print("   1. CLICK AND DRAG to draw rectangle around BOTH dancers")
    print("   2. Make the rectangle LARGE (include space around them)")
    print("   3. Press ENTER to start tracking")
    print()

    # Redimensionner pour affichage
    display_frame = frame.copy()
    scale = 1.0
    max_display_height = 1000

    if height > max_display_height:
        scale = max_display_height / height
        display_width = int(width * scale)
        display_height = int(height * scale)
        display_frame = cv2.resize(frame, (display_width, display_height))
        print(f"Display scaled to {display_width}x{display_height}")
        print()

    bbox = cv2.selectROI("Select dancers (ENTER to validate)", display_frame, False, False)
    cv2.destroyWindow("Select dancers (ENTER to validate)")

    # Rescale bbox si nécessaire
    if scale != 1.0:
        bbox = tuple(int(val / scale) for val in bbox)

    if bbox == (0, 0, 0, 0) or bbox[2] == 0 or bbox[3] == 0:
        print("ERROR: Invalid selection")
        video.release()
        sys.exit(1)

    initial_bbox = bbox
    print(f"Selected area: x={bbox[0]}, y={bbox[1]}, w={bbox[2]}, h={bbox[3]}")
    print()

    # Créer le tracker
    print(f"Creating {tracker_type} tracker...")

    if tracker_type == "CSRT":
        tracker = cv2.TrackerCSRT_create()
    elif tracker_type == "KCF":
        tracker = cv2.legacy.TrackerKCF_create()
    elif tracker_type == "MOSSE":
        tracker = cv2.legacy.TrackerMOSSE_create()
    elif tracker_type == "MIL":
        tracker = cv2.legacy.TrackerMIL_create()
    else:
        print(f"Unknown tracker type: {tracker_type}, using CSRT")
        tracker = cv2.TrackerCSRT_create()

    tracker.init(frame, bbox)

    # Variables de tracking
    coords = []
    frame_count = start_frame

    # Statistiques pour détecter les problèmes
    initial_area = bbox[2] * bbox[3]
    lost_count = 0
    size_history = [initial_area]

    print("Tracking started...")
    print()
    print("CONTROLS:")
    print("   ESC = Stop tracking")
    print("   R = Re-initialize (select dancers again)")
    print("   SPACE = Pause/Resume")
    print()

    paused = False

    while True:
        if not paused:
            ok, frame = video.read()
            if not ok:
                break

            frame_count += 1

            # Mettre à jour le tracker
            ok, bbox = tracker.update(frame)

            if ok:
                (x, y, w, h) = [int(v) for v in bbox]
                current_area = w * h
                size_history.append(current_area)

                # Garder seulement les 30 dernières frames
                if len(size_history) > 30:
                    size_history.pop(0)

                coords.append((frame_count, x, y, w, h))

                # Détecter les problèmes
                area_ratio = current_area / initial_area
                recent_avg_area = sum(size_history) / len(size_history)
                size_change = abs(current_area - recent_avg_area) / recent_avg_area

                # WARNING si le rectangle devient trop petit
                color = (0, 255, 0)  # Vert = OK
                status = "OK"

                if area_ratio < 0.3:
                    color = (0, 0, 255)  # Rouge = MAUVAIS
                    status = "WARNING: Box too small!"
                    lost_count += 1
                elif area_ratio < 0.5:
                    color = (0, 165, 255)  # Orange = ATTENTION
                    status = "ATTENTION: Box shrinking"
                elif size_change > 0.2:
                    color = (0, 165, 255)
                    status = "ATTENTION: Sudden size change"

                # Dessiner le rectangle
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 3)

                # Informations
                cv2.putText(frame, f"Frame: {frame_count}/{total_frames}",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                cv2.putText(frame, f"Size: {w}x{h} (ratio: {area_ratio:.2f})",
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                cv2.putText(frame, status,
                           (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                cv2.putText(frame, "R=Reinit SPACE=Pause ESC=Stop",
                           (10, height-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            else:
                lost_count += 1
                cv2.putText(frame, "TRACKING LOST! Press R to reinitialize",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            # Afficher la progression
            if frame_count % 30 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"   Progress: {progress:.1f}% ({frame_count}/{total_frames}) - Lost: {lost_count} times")

        # Afficher la frame
        display_frame = frame
        max_width = 800
        max_height = 1000

        if width > max_width or height > max_height:
            scale_w = max_width / width if width > max_width else 1.0
            scale_h = max_height / height if height > max_height else 1.0
            scale = min(scale_w, scale_h)
            display_frame = cv2.resize(frame, None, fx=scale, fy=scale)

        cv2.imshow("Tracking (ESC=Stop, R=Reinit, SPACE=Pause)", display_frame)

        # Gestion des touches
        key = cv2.waitKey(1) & 0xFF

        if key == 27:  # ESC
            print("\nStopping...")
            break
        elif key == ord('r') or key == ord('R'):  # R pour réinitialiser
            print("\n*** REINITIALIZING - Select dancers again ***")
            paused = True

            # Redimensionner pour affichage
            display_frame_select = frame.copy()
            if height > max_display_height:
                display_frame_select = cv2.resize(frame, (display_width, display_height))

            bbox = cv2.selectROI("Select dancers again (ENTER to validate)", display_frame_select, False, False)
            cv2.destroyWindow("Select dancers again (ENTER to validate)")

            if scale != 1.0:
                bbox = tuple(int(val / scale) for val in bbox)

            if bbox != (0, 0, 0, 0) and bbox[2] > 0 and bbox[3] > 0:
                # Créer un nouveau tracker
                if tracker_type == "CSRT":
                    tracker = cv2.TrackerCSRT_create()
                elif tracker_type == "KCF":
                    tracker = cv2.legacy.TrackerKCF_create()
                else:
                    tracker = cv2.TrackerCSRT_create()

                tracker.init(frame, bbox)
                initial_area = bbox[2] * bbox[3]
                size_history = [initial_area]
                print(f"Reinitialized at frame {frame_count}")
                paused = False
            else:
                print("Invalid selection, continuing with old tracker")
                paused = False

        elif key == ord(' '):  # SPACE pour pause
            paused = not paused
            if paused:
                print("PAUSED")
            else:
                print("RESUMED")

    video.release()
    cv2.destroyAllWindows()

    print()
    print(f"Tracking completed! {len(coords)} frames tracked")
    print(f"Lost tracking {lost_count} times")
    print()

    # Sauvegarder
    print(f"Saving coordinates to '{output_csv}'...")
    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "x", "y", "w", "h"])
        writer.writerows(coords)

    print(f"File '{output_csv}' created successfully!")
    print()
    print("Statistics:")
    print(f"   Frames tracked: {len(coords)}/{total_frames}")
    print(f"   Success rate: {(len(coords)/total_frames)*100:.1f}%")

    return output_csv


def main():
    if len(sys.argv) < 2:
        print("Usage: python track_dancers_improved.py <video_path> [output.csv] [options]")
        print("\nExample:")
        print("  python track_dancers_improved.py video.mov")
        print("  python track_dancers_improved.py video.mov coords.csv --start-time 30 --tracker KCF")
        print("\nOptions:")
        print("  --start-time SECONDS    Start tracking from this time (default: 0)")
        print("  --tracker TYPE          Tracker type: CSRT, KCF, MOSSE, MIL (default: CSRT)")
        sys.exit(1)

    video_path = sys.argv[1]
    output_csv = "coords.csv"
    start_time = 0
    tracker_type = "CSRT"

    # Parse arguments
    i = 2
    if i < len(sys.argv) and not sys.argv[i].startswith('--'):
        output_csv = sys.argv[i]
        i += 1

    while i < len(sys.argv):
        if sys.argv[i] == '--start-time' and i + 1 < len(sys.argv):
            start_time = float(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--tracker' and i + 1 < len(sys.argv):
            tracker_type = sys.argv[i + 1].upper()
            i += 2
        else:
            i += 1

    select_and_track_improved(video_path, output_csv, start_time, tracker_type)


if __name__ == "__main__":
    main()
