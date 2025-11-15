"""
Export Thread for Dancer Tracking UI
Runs video export in background without blocking the UI
"""

import cv2
import csv
import os
import subprocess
import numpy as np
import tempfile
from PyQt5.QtCore import QThread, pyqtSignal


def parse_aspect_ratio(aspect_ratio_str):
    """
    Parse aspect ratio string and return (width, height, ratio_value)

    Returns:
        tuple: (target_width, target_height, ratio) or None if 'auto'
    """
    if aspect_ratio_str is None or aspect_ratio_str.lower() == 'auto':
        return None

    # Instagram presets
    if aspect_ratio_str.lower() in ['instagram', '4:5']:
        return (1080, 1350, 0.8)  # 4:5 portrait

    if aspect_ratio_str.lower() in ['square', '1:1']:
        return (1080, 1080, 1.0)  # Square

    if aspect_ratio_str.lower() in ['9:16', 'iphone']:
        return (1080, 1920, 0.5625)  # Vertical iPhone

    if aspect_ratio_str.lower() in ['16:9', 'landscape']:
        return (1920, 1080, 1.777)  # Landscape

    # Parse custom ratio like "4:5" or "16:9"
    if ':' in aspect_ratio_str:
        try:
            w_ratio, h_ratio = map(int, aspect_ratio_str.split(':'))
            ratio = w_ratio / h_ratio
            # Calculate dimensions maintaining ~1080p quality
            if ratio < 1:  # Portrait
                height = 1350
                width = int(height * ratio)
            else:  # Landscape
                width = 1920
                height = int(width / ratio)
            return (width, height, ratio)
        except:
            return None

    return None


def calculate_adaptive_crop(x, y, w, h, target_ratio, video_width, video_height, margin_factor=1.5, min_width=1080, min_height=1350):
    """
    Calculate ADAPTIVE crop that maintains aspect ratio but adjusts size to fit dancer
    (Same as in export_final.py)
    """
    required_w = int(w * margin_factor)
    required_h = int(h * margin_factor)

    required_w = max(required_w, min_width)
    required_h = max(required_h, min_height)

    if required_w / required_h > target_ratio:
        crop_w = required_w
        crop_h = int(crop_w / target_ratio)
    else:
        crop_h = required_h
        crop_w = int(crop_h * target_ratio)

    if crop_w > video_width:
        crop_w = video_width
        crop_h = int(crop_w / target_ratio)
    if crop_h > video_height:
        crop_h = video_height
        crop_w = int(crop_h * target_ratio)

    crop_w = min(crop_w, video_width)
    crop_h = min(crop_h, video_height)

    actual_ratio = crop_w / crop_h
    if abs(actual_ratio - target_ratio) > 0.01:
        if crop_w == video_width:
            crop_h = int(crop_w / target_ratio)
            if crop_h > video_height:
                crop_h = video_height
        else:
            crop_w = int(crop_h * target_ratio)
            if crop_w > video_width:
                crop_w = video_width

    center_x = x + w // 2
    center_y = y + h // 2
    crop_x = center_x - crop_w // 2
    crop_y = center_y - crop_h // 2

    if crop_x < 0:
        crop_x = 0
    if crop_y < 0:
        crop_y = 0
    if crop_x + crop_w > video_width:
        crop_x = video_width - crop_w
    if crop_y + crop_h > video_height:
        crop_y = video_height - crop_h

    return crop_x, crop_y, crop_w, crop_h


def smooth_crop_sizes(crop_sizes, smooth_window=30):
    """
    Smooth crop size changes using EMA
    (Same as in export_final.py)
    """
    if len(crop_sizes) < 2:
        return crop_sizes

    alpha = 2.0 / (smooth_window + 1)
    smoothed = []
    ema_w = crop_sizes[0][0]
    ema_h = crop_sizes[0][1]

    for crop_w, crop_h in crop_sizes:
        ema_w = alpha * crop_w + (1 - alpha) * ema_w
        ema_h = alpha * crop_h + (1 - alpha) * ema_h
        smoothed.append((int(ema_w), int(ema_h)))

    return smoothed


class ExportThread(QThread):
    """Thread for running export in background"""

    # Signals
    progress_update = pyqtSignal(int, int, str)  # current_frame, total_frames, status_text
    export_complete = pyqtSignal(str)  # output_path
    export_error = pyqtSignal(str)  # error_message

    def __init__(self, video_path, coords_csv, output_path, margin_factor=1.5, smooth_window=10, aspect_ratio=None, adaptive_crop=False):
        super().__init__()
        self.video_path = video_path
        self.coords_csv = coords_csv
        self.output_path = output_path
        self.margin_factor = margin_factor
        self.smooth_window = smooth_window
        self.aspect_ratio = aspect_ratio
        self.adaptive_crop = adaptive_crop

        # Control flags
        self.should_stop = False

    def stop(self):
        """Stop export"""
        self.should_stop = True

    def run(self):
        """Main export loop - runs in background thread"""
        try:
            # Validate inputs
            if not os.path.exists(self.video_path):
                self.export_error.emit(f"Video file not found: {self.video_path}")
                return

            if not os.path.exists(self.coords_csv):
                self.export_error.emit(f"Coordinates file not found: {self.coords_csv}")
                return

            self.progress_update.emit(0, 100, "Loading video...")

            # Open video
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self.export_error.emit("Cannot open video file")
                return

            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            self.progress_update.emit(5, 100, "Loading coordinates...")

            # Load coordinates
            coords = self._load_coordinates(self.coords_csv)
            if not coords:
                self.export_error.emit("No coordinates found in CSV")
                cap.release()
                return

            self.progress_update.emit(10, 100, "Interpolating gaps...")

            # Interpolate missing frames
            coords = self._interpolate_gaps(coords)

            self.progress_update.emit(15, 100, "Stabilizing coordinates...")

            # Stabilize and smooth
            coords = self._stabilize_and_smooth(coords, self.smooth_window)

            # Parse aspect ratio
            aspect_info = parse_aspect_ratio(self.aspect_ratio)

            # Variables for adaptive mode
            use_adaptive = False
            adaptive_crop_sizes = None

            if aspect_info is not None:
                # Fixed aspect ratio mode
                target_w, target_h, target_ratio = aspect_info

                if self.adaptive_crop:
                    self.progress_update.emit(18, 100, f"Using ADAPTIVE {self.aspect_ratio} (prevents cut-offs)")
                    use_adaptive = True
                else:
                    self.progress_update.emit(18, 100, f"Using {self.aspect_ratio} aspect ratio")

                # Ensure dimensions fit within video
                if target_w > width or target_h > height:
                    # Scale down to fit
                    scale = min(width / target_w, height / target_h)
                    target_w = int(target_w * scale)
                    target_h = int(target_h * scale)

                if use_adaptive:
                    # Pre-calculate adaptive crop sizes
                    self.progress_update.emit(19, 100, "Calculating adaptive crop sizes...")
                    raw_crop_sizes = []

                    for frame_num, x, y, w, h in coords:
                        _, _, adaptive_w, adaptive_h = calculate_adaptive_crop(
                            x, y, w, h, target_ratio, width, height, self.margin_factor, target_w, target_h
                        )
                        raw_crop_sizes.append((adaptive_w, adaptive_h))

                    # Smooth crop sizes
                    smoothed_sizes = smooth_crop_sizes(raw_crop_sizes, self.smooth_window)

                    # Create dict mapping frame number to crop size
                    adaptive_crop_sizes = {}
                    for i, (frame_num, x, y, w, h) in enumerate(coords):
                        adaptive_crop_sizes[frame_num] = smoothed_sizes[i]

                    crop_w = target_w
                    crop_h = target_h
                else:
                    crop_w = target_w
                    crop_h = target_h
            else:
                # Automatic mode - calculate from tracking
                self.progress_update.emit(18, 100, "Using automatic aspect ratio")

                # Calculate fixed crop size using 75th percentile (like export_final.py)
                ws_all = [c[3] for c in coords]
                hs_all = [c[4] for c in coords]
                p75_w = int(np.percentile(ws_all, 75))
                p75_h = int(np.percentile(hs_all, 75))

                crop_w = int(p75_w * self.margin_factor)
                crop_h = int(p75_h * self.margin_factor)

                # Limit to video size
                crop_w = min(crop_w, width)
                crop_h = min(crop_h, height)

            self.progress_update.emit(20, 100, f"Crop size: {crop_w}x{crop_h}")

            # Create temp file for video without audio
            temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            temp_video_path = temp_video.name
            temp_video.close()

            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_video_path, fourcc, fps, (crop_w, crop_h))

            if not out.isOpened():
                self.export_error.emit("Cannot create output video")
                cap.release()
                return

            # Convert coords to dict
            coords_dict = {c[0]: c for c in coords}
            first_tracked_frame = min(coords_dict.keys())

            # Get initial crop position
            first_coord = coords_dict[first_tracked_frame]
            _, x, y, w, h = first_coord
            last_crop_x, last_crop_y, _, _ = self._calculate_fixed_crop(
                x, y, w, h, crop_w, crop_h, width, height
            )

            # Process all frames
            for frame_num in range(total_frames):
                if self.should_stop:
                    out.release()
                    cap.release()
                    os.remove(temp_video_path)
                    self.export_error.emit("Export cancelled by user")
                    return

                # Read frame
                ret, frame = cap.read()
                if not ret:
                    break

                # Get coordinates for this frame
                if frame_num in coords_dict:
                    _, x, y, w, h = coords_dict[frame_num]

                    if use_adaptive and frame_num in adaptive_crop_sizes:
                        # Adaptive mode: use pre-calculated crop size
                        adaptive_w, adaptive_h = adaptive_crop_sizes[frame_num]

                        # Calculate position with adaptive size
                        center_x = x + w // 2
                        center_y = y + h // 2
                        crop_x = center_x - adaptive_w // 2
                        crop_y = center_y - adaptive_h // 2

                        # Bounds checking
                        crop_x = max(0, min(crop_x, width - adaptive_w))
                        crop_y = max(0, min(crop_y, height - adaptive_h))

                        # Crop and resize to target dimensions
                        cropped = frame[crop_y:crop_y+adaptive_h, crop_x:crop_x+adaptive_w]
                        cropped = cv2.resize(cropped, (crop_w, crop_h))
                    else:
                        # Fixed mode
                        crop_x, crop_y, _, _ = self._calculate_fixed_crop(
                            x, y, w, h, crop_w, crop_h, width, height
                        )
                        last_crop_x, last_crop_y = crop_x, crop_y

                        # Crop frame
                        cropped = frame[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]

                        # Handle edge case where crop might be slightly off
                        if cropped.shape[0] != crop_h or cropped.shape[1] != crop_w:
                            cropped = cv2.resize(cropped, (crop_w, crop_h))
                else:
                    # Use last known crop position
                    crop_x, crop_y = last_crop_x, last_crop_y
                    cropped = frame[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]

                    if cropped.shape[0] != crop_h or cropped.shape[1] != crop_w:
                        cropped = cv2.resize(cropped, (crop_w, crop_h))

                # Write frame
                out.write(cropped)

                # Update progress (20-80% for processing)
                progress = 20 + int((frame_num / total_frames) * 60)
                self.progress_update.emit(progress, 100, f"Processing frame {frame_num}/{total_frames}")

            # Release resources
            out.release()
            cap.release()

            if self.should_stop:
                os.remove(temp_video_path)
                self.export_error.emit("Export cancelled by user")
                return

            self.progress_update.emit(80, 100, "Adding audio with FFmpeg...")

            # Add audio using FFmpeg
            success = self._add_audio_with_ffmpeg(temp_video_path, self.video_path, self.output_path)

            # Remove temp file
            try:
                os.remove(temp_video_path)
            except:
                pass

            if success:
                self.progress_update.emit(100, 100, "Export complete!")
                self.export_complete.emit(self.output_path)
            else:
                # If FFmpeg failed, offer the video without audio
                try:
                    import shutil
                    shutil.move(temp_video_path, self.output_path)
                    self.progress_update.emit(100, 100, "Export complete (without audio)")
                    self.export_complete.emit(self.output_path)
                except:
                    self.export_error.emit("Export failed: could not add audio or save video")

        except Exception as e:
            self.export_error.emit(f"Export error: {str(e)}")

    def _load_coordinates(self, csv_path):
        """Load coordinates from CSV"""
        coords = []
        try:
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
        except Exception as e:
            print(f"Error loading coordinates: {e}")
            return []
        return coords

    def _interpolate_gaps(self, coords):
        """Interpolate missing frames"""
        if len(coords) < 2:
            return coords

        result = []

        for i in range(len(coords) - 1):
            current_frame, x1, y1, w1, h1 = coords[i]
            next_frame, x2, y2, w2, h2 = coords[i + 1]

            result.append((current_frame, x1, y1, w1, h1))

            gap_size = next_frame - current_frame - 1

            if gap_size > 0:
                for j in range(1, gap_size + 1):
                    ratio = j / (gap_size + 1)
                    interp_frame = current_frame + j
                    interp_x = int(x1 + (x2 - x1) * ratio)
                    interp_y = int(y1 + (y2 - y1) * ratio)
                    interp_w = int(w1 + (w2 - w1) * ratio)
                    interp_h = int(h1 + (h2 - h1) * ratio)

                    result.append((interp_frame, interp_x, interp_y, interp_w, interp_h))

        result.append(coords[-1])
        return result

    def _stabilize_and_smooth(self, coords, smooth_window=15):
        """Stabilize and smooth coordinates"""
        if len(coords) < smooth_window:
            return coords

        frames = [c[0] for c in coords]
        xs = [c[1] for c in coords]
        ys = [c[2] for c in coords]
        ws = [c[3] for c in coords]
        hs = [c[4] for c in coords]

        # Median size
        median_w = int(np.median(ws))
        median_h = int(np.median(hs))

        # Filter outliers
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

        # Smooth
        smoothed = []
        for i in range(len(frames)):
            start = max(0, i - smooth_window // 2)
            end = min(len(frames), i + smooth_window // 2 + 1)

            avg_x = int(np.mean(xs_filtered[start:end]))
            avg_y = int(np.mean(ys_filtered[start:end]))

            smoothed.append((frames[i], avg_x, avg_y, median_w, median_h))

        return smoothed

    def _calculate_fixed_crop(self, x, y, w, h, target_w, target_h, video_width, video_height):
        """Calculate fixed-size crop centered on tracked region"""
        center_x = x + w // 2
        center_y = y + h // 2

        crop_x = center_x - target_w // 2
        crop_y = center_y - target_h // 2

        # Adjust if out of bounds
        crop_x = max(0, min(crop_x, video_width - target_w))
        crop_y = max(0, min(crop_y, video_height - target_h))

        return crop_x, crop_y, target_w, target_h

    def _add_audio_with_ffmpeg(self, video_path, audio_source, output_path):
        """Add audio from source video using FFmpeg"""
        try:
            # Find FFmpeg
            ffmpeg_exe = self._find_ffmpeg()
            if not ffmpeg_exe:
                return False

            # FFmpeg command to merge video and audio
            cmd = [
                ffmpeg_exe,
                '-i', video_path,  # Video without audio
                '-i', audio_source,  # Original video with audio
                '-c:v', 'libx264',  # H.264 codec
                '-crf', '18',  # Quality (18 = high quality)
                '-c:a', 'aac',  # AAC audio
                '-b:a', '192k',  # Audio bitrate
                '-map', '0:v:0',  # Video from first input
                '-map', '1:a:0',  # Audio from second input
                '-shortest',  # Match shortest stream
                '-y',  # Overwrite output
                output_path
            ]

            # Run FFmpeg
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            return result.returncode == 0

        except Exception as e:
            print(f"FFmpeg error: {e}")
            return False

    def _find_ffmpeg(self):
        """Find FFmpeg executable"""
        # Check local ffmpeg folder first
        local_ffmpeg = os.path.join(os.path.dirname(__file__), 'ffmpeg', 'bin', 'ffmpeg.exe')
        if os.path.exists(local_ffmpeg):
            return local_ffmpeg

        # Try system PATH
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if result.returncode == 0:
                return 'ffmpeg'
        except:
            pass

        return None
