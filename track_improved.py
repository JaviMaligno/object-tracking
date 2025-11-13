#!/usr/bin/env python3
"""
Tracking mejorado con navegación bidireccional e interpolación
Permite avanzar/retroceder durante el tracking
"""

import cv2
import csv
import sys
import os
from pathlib import Path


def select_and_track_improved(video_path, output_csv="coords.csv", start_time=0, tracker_type="CSRT"):
    """
    Tracking mejorado con navegación completa:
    - Retroceder/avanzar frame por frame
    - Saltar segundos adelante/atrás
    - Detección de problemas
    - Reinicialización
    - Interpolación automática de frames no trackeados
    """

    if not os.path.exists(video_path):
        print(f"ERROR: Video '{video_path}' not found")
        sys.exit(1)

    print(f"Opening video: {video_path}")
    video = cv2.VideoCapture(video_path)

    if not video.isOpened():
        print("ERROR: Cannot open video")
        sys.exit(1)

    # Leer la primera frame
    ok, frame = video.read()
    if not ok:
        print("ERROR: Cannot read first frame")
        sys.exit(1)

    # Propiedades del video
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

    # Si start_time especificado, ir a esa posición
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

    # Selección manual inicial
    print("INSTRUCTIONS:")
    print("   1. CLICK AND DRAG to draw rectangle around BOTH dancers")
    print("   2. Make the rectangle LARGE (include space around them)")
    print("   3. Press ENTER to start tracking")
    print()

    # Redimensionar para display
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

    # Rescale bbox si necesario
    if scale != 1.0:
        bbox = tuple(int(val / scale) for val in bbox)

    if bbox == (0, 0, 0, 0) or bbox[2] == 0 or bbox[3] == 0:
        print("ERROR: Invalid selection")
        video.release()
        sys.exit(1)

    initial_bbox = bbox
    print(f"Selected area: x={bbox[0]}, y={bbox[1]}, w={bbox[2]}, h={bbox[3]}")
    print()

    # Crear el tracker
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

    # Variables de tracking - USAR DICCIONARIO
    coords_dict = {}
    current_frame = start_frame

    # Estadísticas
    initial_area = bbox[2] * bbox[3]
    lost_count = 0
    size_history = [initial_area]

    # Estado
    auto_tracking = True
    last_tracked_frame = current_frame - 1
    last_bbox = bbox

    print("Tracking started...")
    print()
    print("CONTROLS:")
    print("   ESC = Stop and save")
    print("   SPACE = Pause/Resume auto-tracking")
    print("   R = Re-initialize tracker")
    print()
    print("   A/D = Navigate ±10 frames")
    print("   W/S = Jump ±5 seconds")
    print()

    while True:
        # Leer el frame actual
        video.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        ok, frame = video.read()

        if not ok:
            if current_frame >= total_frames:
                print("\nEnd of video reached")
                break
            else:
                print(f"\nWarning: Cannot read frame {current_frame}")
                break

        # Determinar si debemos trackear este frame
        should_track = False

        if auto_tracking and current_frame > last_tracked_frame:
            should_track = True

        # Color y status
        color = (128, 128, 128)  # Gris por defecto
        status = "NAVIGATING"

        # Si ya tenemos coordenadas para este frame, mostrarlas
        if current_frame in coords_dict:
            _, x, y, w, h = coords_dict[current_frame]
            color = (0, 255, 0)  # Verde
            status = "TRACKED ✓"
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 3)

        elif should_track:
            # Trackear este frame
            ok, bbox = tracker.update(frame)

            if ok:
                (x, y, w, h) = [int(v) for v in bbox]
                current_area = w * h
                size_history.append(current_area)

                # Mantener solo las últimas 30 frames
                if len(size_history) > 30:
                    size_history.pop(0)

                # Guardar coordenadas
                coords_dict[current_frame] = (current_frame, x, y, w, h)
                last_tracked_frame = current_frame
                last_bbox = bbox

                # Detectar problemas
                area_ratio = current_area / initial_area
                recent_avg_area = sum(size_history) / len(size_history)
                size_change = abs(current_area - recent_avg_area) / recent_avg_area if recent_avg_area > 0 else 0

                color = (0, 255, 0)  # Verde = OK
                status = "TRACKING"

                if area_ratio < 0.3:
                    color = (0, 0, 255)  # Rojo
                    status = "WARNING: Box too small!"
                    lost_count += 1
                elif area_ratio < 0.5:
                    color = (0, 165, 255)  # Naranja
                    status = "ATTENTION: Box shrinking"
                elif size_change > 0.2:
                    color = (0, 165, 255)
                    status = "ATTENTION: Sudden change"

                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 3)
            else:
                lost_count += 1
                color = (0, 0, 255)
                status = "TRACKING LOST! Press R"
                cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                auto_tracking = False  # Parar auto-tracking si se pierde

        elif last_bbox is not None:
            # Mostrar último bbox conocido en gris
            x, y, w, h = [int(v) for v in last_bbox]
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

        # Información en pantalla
        mode_text = "AUTO" if auto_tracking else "MANUAL"
        time_current = current_frame / fps
        time_total = total_frames / fps

        # Línea 1: Frame y tiempo
        cv2.putText(frame, f"Frame: {current_frame}/{total_frames} | {time_current:.1f}/{time_total:.1f}s",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Línea 2: Status y modo
        cv2.putText(frame, f"Status: {status} | Mode: {mode_text}",
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # Línea 3: Coordenadas si hay
        if current_frame in coords_dict or (should_track and ok):
            cv2.putText(frame, f"Box: {w}x{h} | Tracked: {len(coords_dict)} frames",
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Controles en la parte inferior
        controls_y = height - 60
        cv2.putText(frame, "A/D +/-10f | W/S +/-5s",
                   (10, controls_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, "R=Reinit | SPACE=Auto/Manual | ESC=Exit",
                   (10, controls_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Progreso cada 30 frames
        if auto_tracking and current_frame % 30 == 0:
            progress = (current_frame / total_frames) * 100
            print(f"   Progress: {progress:.1f}% ({current_frame}/{total_frames}) - Tracked: {len(coords_dict)} frames")

        # Display
        display_frame = frame
        max_width = 1200
        max_height = 1000

        if width > max_width or height > max_height:
            scale_w = max_width / width if width > max_width else 1.0
            scale_h = max_height / height if height > max_height else 1.0
            scale = min(scale_w, scale_h)
            display_frame = cv2.resize(frame, None, fx=scale, fy=scale)

        cv2.imshow("Tracking (Controls shown on screen)", display_frame)

        # Manejo de teclas - capturar valor completo primero
        key_full = cv2.waitKey(1 if auto_tracking else 30)
        key = key_full & 0xFF

        if key == 27:  # ESC - Salir
            print("\nStopping...")
            break

        elif key == ord(' '):  # SPACE - Toggle auto-tracking
            auto_tracking = not auto_tracking
            if auto_tracking:
                print(f"AUTO-TRACKING RESUMED from frame {current_frame}")
                # Reinicializar tracker con último bbox conocido
                if last_bbox is not None:
                    if tracker_type == "CSRT":
                        tracker = cv2.TrackerCSRT_create()
                    elif tracker_type == "KCF":
                        tracker = cv2.legacy.TrackerKCF_create()
                    elif tracker_type == "MOSSE":
                        tracker = cv2.legacy.TrackerMOSSE_create()
                    else:
                        tracker = cv2.legacy.TrackerMIL_create()
                    tracker.init(frame, last_bbox)
            else:
                print("MANUAL NAVIGATION MODE")

        elif key == ord('r') or key == ord('R'):  # R - Reinicializar
            print(f"\n*** REINITIALIZING at frame {current_frame} ***")

            # Redimensionar para display
            display_frame_select = frame.copy()
            if height > max_display_height:
                display_frame_select = cv2.resize(frame, (display_width, display_height))

            bbox = cv2.selectROI("Select dancers again (ENTER to validate)", display_frame_select, False, False)
            cv2.destroyWindow("Select dancers again (ENTER to validate)")

            if scale != 1.0:
                bbox = tuple(int(val / scale) for val in bbox)

            if bbox != (0, 0, 0, 0) and bbox[2] > 0 and bbox[3] > 0:
                # Crear nuevo tracker
                if tracker_type == "CSRT":
                    tracker = cv2.TrackerCSRT_create()
                elif tracker_type == "KCF":
                    tracker = cv2.legacy.TrackerKCF_create()
                elif tracker_type == "MOSSE":
                    tracker = cv2.legacy.TrackerMOSSE_create()
                else:
                    tracker = cv2.legacy.TrackerMIL_create()

                tracker.init(frame, bbox)
                last_bbox = bbox
                initial_area = bbox[2] * bbox[3]
                size_history = [initial_area]

                # Guardar coordenadas de reinicialización
                x, y, w, h = [int(v) for v in bbox]
                coords_dict[current_frame] = (current_frame, x, y, w, h)
                last_tracked_frame = current_frame

                print(f"Reinitialized at frame {current_frame}")
                auto_tracking = True  # Reanudar auto-tracking
            else:
                print("Invalid selection")

        # Navegación con teclas A/D (10 frames)
        elif key == ord('d') or key == ord('D'):  # D - Derecha 10 frames
            auto_tracking = False
            current_frame = min(current_frame + 10, total_frames - 1)

        elif key == ord('a') or key == ord('A'):  # A - Izquierda 10 frames
            auto_tracking = False
            current_frame = max(current_frame - 10, start_frame)

        # Navegación con teclas W/S (5 segundos)
        elif key == ord('w') or key == ord('W'):  # W - Adelante 5s
            auto_tracking = False
            jump_frames = int(5 * fps)
            current_frame = min(current_frame + jump_frames, total_frames - 1)
            print(f"Jumped to frame {current_frame} (+5s)")

        elif key == ord('s') or key == ord('S'):  # S - Atrás 5s
            auto_tracking = False
            jump_frames = int(5 * fps)
            current_frame = max(current_frame - jump_frames, start_frame)
            print(f"Jumped to frame {current_frame} (-5s)")

        # PageUp/PageDown (si funcionan)
        elif key == 33:  # PageUp
            auto_tracking = False
            jump_frames = int(30 * fps)
            current_frame = min(current_frame + jump_frames, total_frames - 1)
            print(f"Jumped to frame {current_frame} (+30s)")

        elif key == 34:  # PageDown
            auto_tracking = False
            jump_frames = int(30 * fps)
            current_frame = max(current_frame - jump_frames, start_frame)
            print(f"Jumped to frame {current_frame} (-30s)")

        # Avanzar frame si estamos en auto-tracking
        if auto_tracking:
            current_frame += 1
            if current_frame >= total_frames:
                print("\nEnd of video reached")
                break

    video.release()
    cv2.destroyAllWindows()

    print()
    print(f"Tracking completed!")
    print(f"   Frames tracked: {len(coords_dict)}")
    print(f"   Total frames: {total_frames}")
    print(f"   Coverage: {(len(coords_dict)/total_frames)*100:.1f}%")
    print(f"   Lost tracking: {lost_count} times")
    print()

    # Convertir diccionario a lista ordenada
    coords = sorted(coords_dict.values(), key=lambda x: x[0])

    # Guardar
    print(f"Saving coordinates to '{output_csv}'...")
    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "x", "y", "w", "h"])
        writer.writerows(coords)

    print(f"File '{output_csv}' created successfully!")
    print()

    # Detectar gaps
    if len(coords) > 1:
        gaps = []
        for i in range(len(coords) - 1):
            gap_size = coords[i+1][0] - coords[i][0] - 1
            if gap_size > 0:
                gaps.append((coords[i][0], coords[i+1][0], gap_size))

        if gaps:
            print(f"Found {len(gaps)} gaps in tracking:")
            for start, end, size in gaps[:5]:  # Mostrar solo los primeros 5
                print(f"   Frames {start} to {end}: {size} frames will be interpolated")
            if len(gaps) > 5:
                print(f"   ... and {len(gaps) - 5} more gaps")
            print()
            print("These gaps will be interpolated during export.")
        else:
            print("No gaps found - complete continuous tracking!")

    print()
    print("Statistics:")
    print(f"   Frames tracked: {len(coords)}/{total_frames}")
    print(f"   Success rate: {(len(coords)/total_frames)*100:.1f}%")

    return output_csv


def main():
    if len(sys.argv) < 2:
        print("Usage: python track_improved.py <video_path> [output.csv] [options]")
        print("\nExample:")
        print("  python track_improved.py video.mov")
        print("  python track_improved.py video.mov coords.csv --start-time 30 --tracker KCF")
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
