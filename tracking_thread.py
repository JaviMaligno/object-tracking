"""
Tracking Thread for Dancer Tracking UI
Runs tracking in background without blocking the UI

ARCHITECTURE: This is a THIN WRAPPER around TrackerCore from track_improved.py.
It bridges PyQt signals to the original tracking logic without reimplementing it.
"""

import cv2
import time
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

# Import the original tracking logic
from track_improved import TrackerCore


class TrackingThread(QThread):
    """Thread for running tracking in background using TrackerCore"""

    # Signals to communicate with UI
    progress_update = pyqtSignal(int, int, str)  # frame, total_frames, status_text
    frame_tracked = pyqtSignal(int, object, str, object)  # frame_number, bbox (x,y,w,h) or None, color, frame_cv
    tracking_complete = pyqtSignal(dict)  # coords_dict
    tracking_error = pyqtSignal(str)  # error_message
    request_bbox = pyqtSignal(int)  # Requests bbox selection for frame_number

    def __init__(self, video_path, tracker_type="KCF", start_frame=0):
        super().__init__()
        self.video_path = video_path
        self.tracker_type = tracker_type
        self.start_frame = start_frame

        # Control flags for thread
        self.is_running = False
        self.should_stop = False
        self.should_reinitialize = False

        # TrackerCore instance (created in run())
        self.core = None

        # Initial bbox (set by UI before starting)
        self.initial_bbox = None
        self.reinitialize_bbox = None

    def set_initial_bbox(self, bbox):
        """Set the initial bounding box (x, y, w, h)"""
        self.initial_bbox = bbox

    def set_reinitialize_bbox(self, bbox):
        """Set bbox for reinitialization"""
        self.reinitialize_bbox = bbox
        self.should_reinitialize = False

    def pause(self):
        """Pause tracking - forwards to TrackerCore"""
        if self.core:
            self.core.auto_tracking = False

    def resume(self):
        """Resume tracking - forwards to TrackerCore"""
        if self.core:
            self.core.toggle_auto_tracking()

    def stop(self):
        """Stop tracking"""
        self.should_stop = True

    def request_reinitialize(self):
        """Request tracker reinitialization"""
        self.should_reinitialize = True
        if self.core:
            self.core.auto_tracking = False

    def handle_key(self, key):
        """Forward keyboard event to TrackerCore - THIS IS CRITICAL"""
        if self.core:
            self.core.handle_key(key)

    def set_current_frame(self, frame_number):
        """Update current frame position (for manual navigation)"""
        if self.core:
            self.core.current_frame = frame_number

    @property
    def is_paused(self):
        """Check if tracking is paused"""
        if self.core:
            return not self.core.auto_tracking
        return False

    @property
    def current_frame(self):
        """Get current frame number"""
        if self.core:
            return self.core.current_frame
        return 0

    @property
    def total_frames(self):
        """Get total frame count"""
        if self.core:
            return self.core.total_frames
        return 0

    @property
    def coords_dict(self):
        """Get coordinates dictionary"""
        if self.core:
            return self.core.coords_dict
        return {}

    def run(self):
        """Main tracking loop - thin wrapper around TrackerCore"""
        try:
            self.is_running = True
            self.should_stop = False

            # Create TrackerCore instance with original logic
            self.core = TrackerCore(
                video_path=self.video_path,
                tracker_type=self.tracker_type,
                start_frame=self.start_frame
            )

            # Open video using original logic
            if not self.core.open_video():
                self.tracking_error.emit("Cannot open video file")
                return

            # Wait for initial bbox if not set
            if self.initial_bbox is None:
                self.request_bbox.emit(self.core.current_frame)
                while self.initial_bbox is None and not self.should_stop:
                    time.sleep(0.1)

            if self.should_stop:
                return

            # Initialize tracker using original logic (reads frame internally)
            if not self.core.initialize_tracker(self.initial_bbox):
                self.tracking_error.emit(f"Failed to create {self.tracker_type} tracker")
                return

            # CRITICAL: Show the initialized frame immediately (matches original behavior)
            # In the original, after tracker.init(), the loop reads the current frame again
            # and displays it. We need to replicate this.
            self.core.video.set(cv2.CAP_PROP_POS_FRAMES, self.core.current_frame)
            ok, frame = self.core.video.read()
            if ok:
                # The bbox was just initialized, show it with green color
                # initial_bbox is (x, y, w, h) - 4 values
                x, y, w, h = self.initial_bbox
                bbox = (int(x), int(y), int(w), int(h))
                frame_copy = frame.copy()
                self.frame_tracked.emit(self.core.current_frame, bbox, 'green', frame_copy)

            self.progress_update.emit(self.core.current_frame, self.core.total_frames, "Initialized - Press Resume/Space to start")

            # Start in PAUSED state - user must manually resume (same as original)
            self.core.auto_tracking = False

            # Main tracking loop - use original logic
            while self.core.current_frame < self.core.total_frames and not self.should_stop:
                # Handle pause (wait while not auto_tracking)
                while not self.core.auto_tracking and not self.should_stop:
                    time.sleep(0.1)

                    # Handle manual reinitialization (user pressed R)
                    if self.should_reinitialize:
                        self.request_bbox.emit(self.core.current_frame)

                        # Wait for bbox to be set
                        while self.should_reinitialize and not self.should_stop:
                            time.sleep(0.1)

                        if self.should_stop:
                            break

                        # Reinitialize using original logic
                        # CRITICAL: Must show the reinitialized frame BEFORE auto-tracking resumes
                        # This matches original behavior where loop shows current frame after reinit
                        if self.reinitialize_bbox:
                            if self.core.reinitialize(self.reinitialize_bbox):
                                # Read the frame we just reinitialized on
                                self.core.video.set(cv2.CAP_PROP_POS_FRAMES, self.core.current_frame)
                                ok, frame = self.core.video.read()

                                if ok and self.core.current_frame in self.core.coords_dict:
                                    # Get the bbox we just saved in coords_dict
                                    _, x, y, w, h = self.core.coords_dict[self.core.current_frame]
                                    bbox = (int(x), int(y), int(w), int(h))

                                    # Emit the reinitialized frame with green bbox
                                    frame_copy = frame.copy()
                                    self.frame_tracked.emit(self.core.current_frame, bbox, 'green', frame_copy)

                                self.progress_update.emit(
                                    self.core.current_frame,
                                    self.core.total_frames,
                                    "Reinitialized - Resuming"
                                )

                if self.should_stop:
                    break

                # Process frame using ORIGINAL LOGIC from TrackerCore
                result = self.core.process_frame()

                if result is None:
                    # Video ended
                    break

                # Emit signals based on result
                frame_cv = result['frame']  # OpenCV frame (BGR numpy array)
                frame_number = result['frame_number']
                bbox = result['bbox']
                color_bgr = result['color']  # BGR tuple from OpenCV
                status = result['status']
                mode = result['mode']

                # Convert BGR color to string for UI
                if color_bgr == (0, 255, 0):  # Green
                    color = 'green'
                elif color_bgr == (0, 165, 255):  # Orange
                    color = 'orange'
                elif color_bgr == (0, 0, 255):  # Red
                    color = 'red'
                elif color_bgr == (128, 128, 128):  # Gray
                    color = 'gray'
                else:
                    color = 'green'

                # Update progress
                self.progress_update.emit(frame_number, self.core.total_frames, status)

                # Copy frame to avoid threading issues with numpy arrays
                # Qt signals serialize data, so we need to ensure frame is independent
                frame_copy = frame_cv.copy()

                # Emit frame tracking result WITH frame data for display
                if bbox:
                    self.frame_tracked.emit(frame_number, bbox, color, frame_copy)
                else:
                    # Tracking lost
                    self.frame_tracked.emit(frame_number, None, 'red', frame_copy)

                # Small delay to not overwhelm the UI and FFmpeg decoder
                # 20ms gives FFmpeg decoder sufficient time to process frames
                # Combined with sequential read optimization in process_frame(),
                # this ensures stable operation without async_lock errors
                time.sleep(0.02)

            # Complete tracking
            if self.core.coords_dict and not self.should_stop:
                self.tracking_complete.emit(self.core.coords_dict)
            else:
                self.tracking_error.emit("Tracking stopped by user")

        except Exception as e:
            import traceback
            self.tracking_error.emit(f"Tracking error: {str(e)}\n{traceback.format_exc()}")

        finally:
            if self.core:
                self.core.close()
            self.is_running = False

    def save_to_csv(self, output_path):
        """Save tracking coordinates to CSV file"""
        if not self.core or not self.core.coords_dict:
            return False

        try:
            import csv
            sorted_frames = sorted(self.core.coords_dict.keys())
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['frame', 'x', 'y', 'w', 'h'])

                for frame_num in sorted_frames:
                    frame, x, y, w, h = self.core.coords_dict[frame_num]
                    writer.writerow([frame, x, y, w, h])

            return True
        except Exception as e:
            print(f"Error saving CSV: {e}")
            return False
