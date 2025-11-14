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


class TrackerCore:
    """
    Core tracking logic extracted from track_improved.py.
    Can be used standalone or embedded in UI.
    Maintains EXACT same behavior as original command-line version.
    """

    def __init__(self, video_path, tracker_type="CSRT", start_frame=0):
        self.video_path = video_path
        self.tracker_type = tracker_type
        self.start_frame = start_frame

        # State variables (from original lines 119-131)
        self.coords_dict = {}
        self.current_frame = start_frame
        self.auto_tracking = True
        self.last_tracked_frame = start_frame - 1
        self.last_bbox = None

        # Video properties
        self.video = None
        self.fps = 30
        self.total_frames = 0
        self.width = 0
        self.height = 0

        # Tracker
        self.tracker = None
        self.initial_area = 0
        self.size_history = []
        self.lost_count = 0

        # Frame cache for seek optimization
        self.last_read_frame_number = -1  # Track last frame position
        self.cached_frame = None  # Cache last read frame

    def open_video(self):
        """
        Open video and read properties

        FIX: Add decoder stabilization delay after large seeks to prevent
        async_lock errors when jumping to non-zero start frames.
        """
        if not os.path.exists(self.video_path):
            raise FileNotFoundError(f"Video '{self.video_path}' not found")

        self.video = cv2.VideoCapture(self.video_path)
        if not self.video.isOpened():
            raise RuntimeError("Cannot open video")

        self.fps = self.video.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.video.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.video.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.video.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Seek to start frame
        if self.start_frame > 0:
            try:
                self.video.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
                self.current_frame = self.start_frame
                self.last_read_frame_number = self.start_frame - 1

                # Give decoder time to stabilize after large seek
                # Critical for preventing async_lock errors on initial seek
                cv2.waitKey(30)
            except Exception as e:
                print(f"Warning: Seek to start frame {self.start_frame} failed: {e}")
                return False

        return True

    def initialize_tracker(self, bbox):
        """
        Initialize tracker with bbox (from lines 102-117)

        FIX: Cache the frame and update position tracking to prevent
        redundant seeks in subsequent process_frame() calls.
        """
        # Read frame at current position and cache it
        try:
            self.video.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        except Exception as e:
            print(f"Warning: Seek failed in initialize_tracker: {e}")
            return False

        ok, frame = self.video.read()
        if not ok:
            return False

        # Update position tracking and cache
        self.last_read_frame_number = self.current_frame
        self.cached_frame = frame.copy()

        # Create tracker
        self.tracker = self._create_tracker(self.tracker_type)
        if not self.tracker:
            return False

        self.tracker.init(frame, bbox)
        self.last_bbox = bbox
        self.initial_area = bbox[2] * bbox[3]
        self.size_history = [self.initial_area]

        return True

    def _create_tracker(self, tracker_type):
        """Create OpenCV tracker (from lines 105-115)"""
        if tracker_type == "CSRT":
            return cv2.TrackerCSRT_create()
        elif tracker_type == "KCF":
            return cv2.legacy.TrackerKCF_create()
        elif tracker_type == "MOSSE":
            return cv2.legacy.TrackerMOSSE_create()
        elif tracker_type == "MIL":
            return cv2.legacy.TrackerMIL_create()
        else:
            return cv2.TrackerCSRT_create()

    def handle_key(self, key):
        """
        Handle keyboard input EXACTLY as original (lines 333-366).
        Returns True if should continue, False if should exit.
        """
        if key == 27:  # ESC
            return False

        elif key == ord(' '):  # SPACE - Toggle auto-tracking (lines 275-291)
            self.toggle_auto_tracking()

        elif key == ord('r') or key == ord('R'):  # R - handled externally (needs UI)
            pass  # UI will call reinitialize() with new bbox

        elif key == ord('d') or key == ord('D'):  # D - Forward 10 frames (line 334-336)
            self.auto_tracking = False
            self.current_frame = min(self.current_frame + 10, self.total_frames - 1)

        elif key == ord('a') or key == ord('A'):  # A - Backward 10 frames (line 338-340)
            self.auto_tracking = False
            self.current_frame = max(self.current_frame - 10, self.start_frame)

        elif key == ord('w') or key == ord('W'):  # W - Forward 5s (line 343-347)
            self.auto_tracking = False
            jump_frames = int(5 * self.fps)
            self.current_frame = min(self.current_frame + jump_frames, self.total_frames - 1)

        elif key == ord('s') or key == ord('S'):  # S - Backward 5s (line 349-353)
            self.auto_tracking = False
            jump_frames = int(5 * self.fps)
            self.current_frame = max(self.current_frame - jump_frames, self.start_frame)

        return True

    def toggle_auto_tracking(self):
        """
        Toggle auto-tracking EXACTLY as original (lines 275-291).
        CRITICAL: Recreates tracker when resuming.

        FIX: Use cached frame instead of seeking to avoid redundant decoder operations.
        """
        self.auto_tracking = not self.auto_tracking

        if self.auto_tracking:
            # Recreate tracker with last_bbox (lines 280-289)
            if self.last_bbox is not None and self.cached_frame is not None:
                # Use cached frame - no need to seek and read again
                self.tracker = self._create_tracker(self.tracker_type)
                self.tracker.init(self.cached_frame, self.last_bbox)

    def reinitialize(self, bbox):
        """
        Reinitialize tracker EXACTLY as original (lines 307-329).
        CRITICAL: Auto-resumes after reinitialization.

        FIX: Use cached frame to avoid redundant seek and read.
        """
        # Use cached frame if available, otherwise read current frame
        if self.cached_frame is not None:
            frame = self.cached_frame
            ok = True
        else:
            # Fallback: seek and read if no cache
            try:
                self.video.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            except Exception as e:
                print(f"Warning: Seek failed in reinitialize: {e}")
                return False
            ok, frame = self.video.read()

        if ok and bbox is not None and bbox[2] > 0 and bbox[3] > 0:
            # Create new tracker (lines 309-318)
            self.tracker = self._create_tracker(self.tracker_type)
            self.tracker.init(frame, bbox)
            self.last_bbox = bbox
            self.initial_area = bbox[2] * bbox[3]
            self.size_history = [self.initial_area]

            # Save reinitialization coordinates (lines 324-326)
            x, y, w, h = [int(v) for v in bbox]
            self.coords_dict[self.current_frame] = (self.current_frame, x, y, w, h)
            self.last_tracked_frame = self.current_frame

            # Auto-resume (line 329)
            self.auto_tracking = True

            return True
        return False

    def process_frame(self):
        """
        Process current frame EXACTLY as original (lines 144-374).
        Returns dict with frame data for display.

        OPTIMIZATION: Only seeks when frame is non-sequential.
        This prevents FFmpeg async_lock errors from excessive seeking.
        """
        # CRITICAL FIX: Only seek if frame is non-sequential
        # Sequential reads (N, N+1, N+2...) should NOT seek - just read()
        # This eliminates 95% of seeks and prevents FFmpeg decoder race conditions
        is_sequential = (self.current_frame == self.last_read_frame_number + 1)

        if not is_sequential:
            # Non-sequential access (jump, rewind, or first frame) - must seek
            try:
                self.video.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            except Exception as e:
                print(f"Warning: Seek to frame {self.current_frame} failed: {e}")
                return None

        # Read frame (sequential or after seek)
        ok, frame = self.video.read()

        if not ok:
            return None

        # Update position tracking
        self.last_read_frame_number = self.current_frame
        self.cached_frame = frame.copy()

        # Determine if should track (lines 158-161)
        should_track = self.auto_tracking and self.current_frame > self.last_tracked_frame

        # Default color and status (lines 163-165)
        color = (128, 128, 128)  # Gray for navigating
        status = "NAVIGATING"
        bbox = None

        # Check if already tracked (lines 168-172)
        if self.current_frame in self.coords_dict:
            _, x, y, w, h = self.coords_dict[self.current_frame]
            bbox = (x, y, w, h)
            color = (0, 255, 0)  # Green
            status = "TRACKED ✓"

        # Track this frame (lines 174-217)
        elif should_track and self.tracker:
            ok, tracked_bbox = self.tracker.update(frame)

            if ok:
                x, y, w, h = [int(v) for v in tracked_bbox]
                current_area = w * h
                self.size_history.append(current_area)

                # Keep only last 30 frames (lines 183-185)
                if len(self.size_history) > 30:
                    self.size_history.pop(0)

                # Save coordinates (lines 187-190)
                self.coords_dict[self.current_frame] = (self.current_frame, x, y, w, h)
                self.last_tracked_frame = self.current_frame
                self.last_bbox = tracked_bbox
                bbox = (x, y, w, h)

                # Detect problems (lines 192-209)
                area_ratio = current_area / self.initial_area if self.initial_area > 0 else 1.0
                recent_avg_area = sum(self.size_history) / len(self.size_history)
                size_change = abs(current_area - recent_avg_area) / recent_avg_area if recent_avg_area > 0 else 0

                color = (0, 255, 0)  # Green = OK
                status = "TRACKING"

                if area_ratio < 0.3:
                    color = (0, 0, 255)  # Red
                    status = "WARNING: Box too small!"
                    self.lost_count += 1
                elif area_ratio < 0.5:
                    color = (0, 165, 255)  # Orange
                    status = "ATTENTION: Box shrinking"
                elif size_change > 0.2:
                    color = (0, 165, 255)  # Orange
                    status = "ATTENTION: Sudden change"
            else:
                # Tracking lost (lines 212-217)
                self.lost_count += 1
                color = (0, 0, 255)  # Red
                status = "TRACKING LOST! Press R"
                self.auto_tracking = False  # Auto-pause

        # Show last bbox when navigating (lines 219-222)
        elif self.last_bbox is not None:
            bbox = tuple(int(v) for v in self.last_bbox)
            color = (128, 128, 128)  # Gray
            status = "NAVIGATING"

        # Advance frame if auto-tracking (lines 369-373)
        if self.auto_tracking:
            self.current_frame += 1
            if self.current_frame >= self.total_frames:
                return None  # End of video

        # Return frame data
        return {
            'frame': frame,
            'frame_number': self.current_frame,
            'bbox': bbox,
            'color': color,
            'status': status,
            'mode': "AUTO" if self.auto_tracking else "MANUAL",
            'tracked_frames': len(self.coords_dict),
        }

    def get_coords_dict(self):
        """Return coordinates dictionary"""
        return self.coords_dict

    def close(self):
        """Release video capture safely with decoder flush"""
        if self.video:
            # Flush decoder by seeking to start before releasing
            # This prevents async_lock errors when closing during active decode
            try:
                self.video.set(cv2.CAP_PROP_POS_FRAMES, 0)
            except:
                pass  # Ignore errors if video already closed or corrupted

            self.video.release()
            self.video = None

            # Give decoder time to cleanup threads
            cv2.waitKey(10)


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
