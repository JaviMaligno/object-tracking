"""
Tracking Thread for Dancer Tracking UI
Runs tracking in background without blocking the UI
"""

import cv2
import csv
import time
from PyQt5.QtCore import QThread, pyqtSignal


class TrackingThread(QThread):
    """Thread for running tracking in background"""

    # Signals
    progress_update = pyqtSignal(int, int, str)  # frame, total_frames, status_text
    frame_tracked = pyqtSignal(int, tuple, str)  # frame_number, bbox (x,y,w,h), color ('green'|'orange'|'red')
    tracking_complete = pyqtSignal(dict)  # coords_dict
    tracking_error = pyqtSignal(str)  # error_message
    request_bbox = pyqtSignal(int)  # Requests bbox selection for frame_number

    def __init__(self, video_path, tracker_type="KCF", start_frame=0):
        super().__init__()
        self.video_path = video_path
        self.tracker_type = tracker_type
        self.start_frame = start_frame

        # Control flags
        self.is_running = False
        self.is_paused = False
        self.should_stop = False
        self.should_reinitialize = False
        self.needs_reinitialization = False  # Flag for auto-reinit after navigation

        # Tracking data
        self.coords_dict = {}
        self.initial_bbox = None
        self.current_bbox = None

        # Video properties
        self.cap = None
        self.fps = 30
        self.total_frames = 0
        self.width = 0
        self.height = 0

        # Current state
        self.current_frame = 0
        self.tracker = None

    def set_initial_bbox(self, bbox):
        """Set the initial bounding box (x, y, w, h)"""
        self.initial_bbox = bbox
        self.current_bbox = bbox

    def set_reinitialize_bbox(self, bbox):
        """Set bbox for reinitialization"""
        self.current_bbox = bbox
        self.should_reinitialize = False  # Reset flag

    def pause(self):
        """Pause tracking"""
        self.is_paused = True

    def resume(self):
        """Resume tracking"""
        self.is_paused = False

    def set_current_frame(self, frame_number):
        """Update current frame position (for manual navigation)"""
        if 0 <= frame_number < self.total_frames:
            self.current_frame = frame_number

    def reinitialize_tracker_at_frame(self, bbox):
        """
        Reinitialize tracker at current frame with given bbox.
        This is critical when resuming after manual navigation - reuses logic from track_improved.py.

        Reads the frame at self.current_frame internally from video capture.

        Args:
            bbox: Bounding box tuple (x, y, w, h)

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.cap or bbox is None:
            return False

        # Read frame at current position (reusing existing video capture)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()

        if not ret:
            return False

        # Create new tracker (reusing existing _create_tracker method)
        self.tracker = self._create_tracker(self.tracker_type)
        if self.tracker is None:
            return False

        # Initialize with current frame and bbox
        self.tracker.init(frame, bbox)
        self.current_bbox = bbox

        return True

    def stop(self):
        """Stop tracking"""
        self.should_stop = True

    def request_reinitialize(self):
        """Request tracker reinitialization"""
        self.should_reinitialize = True
        self.is_paused = True

    def run(self):
        """Main tracking loop - runs in background thread"""
        try:
            self.is_running = True
            self.should_stop = False

            # Open video
            self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                self.tracking_error.emit("Cannot open video file")
                return

            # Get video properties
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Seek to start frame
            self.current_frame = self.start_frame
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)

            # Read first frame
            ret, frame = self.cap.read()
            if not ret:
                self.tracking_error.emit("Cannot read video frames")
                return

            # Wait for initial bbox if not set
            if self.initial_bbox is None:
                self.request_bbox.emit(self.current_frame)
                # Wait for bbox to be set
                while self.initial_bbox is None and not self.should_stop:
                    time.sleep(0.1)

            if self.should_stop:
                return

            # Create tracker
            self.tracker = self._create_tracker(self.tracker_type)
            if self.tracker is None:
                self.tracking_error.emit(f"Failed to create {self.tracker_type} tracker")
                return

            # Initialize tracker
            x, y, w, h = self.initial_bbox
            self.tracker.init(frame, (x, y, w, h))
            initial_area = w * h

            # Save first frame
            self.coords_dict[self.current_frame] = (self.current_frame, x, y, w, h)
            self.frame_tracked.emit(self.current_frame, (x, y, w, h), 'green')

            # Statistics
            size_history = [initial_area]
            last_tracked_frame = self.current_frame

            # Start in PAUSED state - user must manually resume
            self.is_paused = True

            # Main tracking loop
            self.current_frame += 1

            # UI update throttling: update display every N frames (for performance)
            ui_update_interval = 3  # Update UI every 3 frames (~10 fps for 30fps video)
            frames_since_ui_update = 0

            while self.current_frame < self.total_frames and not self.should_stop:
                # Handle pause
                while self.is_paused and not self.should_stop:
                    time.sleep(0.1)

                    # Handle manual reinitialization (user pressed R)
                    if self.should_reinitialize:
                        # Emit signal to request new bbox
                        self.request_bbox.emit(self.current_frame)

                        # Wait for bbox to be set
                        while self.should_reinitialize and not self.should_stop:
                            time.sleep(0.1)

                        if self.should_stop:
                            break

                        # Read current frame
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                        ret, frame = self.cap.read()

                        if ret and self.current_bbox:
                            # Reinitialize tracker
                            self.tracker = self._create_tracker(self.tracker_type)
                            x, y, w, h = self.current_bbox
                            self.tracker.init(frame, (x, y, w, h))

                            # Save coordinates
                            self.coords_dict[self.current_frame] = (self.current_frame, x, y, w, h)
                            self.frame_tracked.emit(self.current_frame, (x, y, w, h), 'green')

                            last_tracked_frame = self.current_frame
                            size_history = [w * h]
                            frames_since_ui_update = 0

                        # DO NOT resume automatically - stay paused
                        # User must manually resume by pressing spacebar or resume button
                        # self.is_paused = False  # Removed - stays paused

                if self.should_stop:
                    break

                # Handle automatic reinitialization after navigation (thread-safe)
                if self.needs_reinitialization:
                    # Find last known bbox
                    reinit_bbox = self.current_bbox
                    if reinit_bbox is None:
                        # Try to find from coords_dict
                        for frame in range(self.current_frame, -1, -1):
                            if frame in self.coords_dict:
                                _, x, y, w, h = self.coords_dict[frame]
                                reinit_bbox = (x, y, w, h)
                                break

                    if reinit_bbox:
                        # Read current frame
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                        ret, frame = self.cap.read()

                        if ret:
                            # Create new tracker (like track_improved.py does)
                            self.tracker = self._create_tracker(self.tracker_type)
                            if self.tracker:
                                x, y, w, h = reinit_bbox
                                self.tracker.init(frame, (x, y, w, h))
                                self.current_bbox = reinit_bbox

                                # Update statistics
                                initial_area = w * h
                                size_history = [initial_area]

                    self.needs_reinitialization = False

                # Read frame at current position
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                ret, frame = self.cap.read()
                if not ret:
                    break

                # Check if we already have coords for this frame (skip tracking)
                if self.current_frame in self.coords_dict:
                    # Frame already tracked - skip and move to next
                    self.current_frame += 1
                    continue

                # Update tracker
                ok, bbox = self.tracker.update(frame)

                if ok:
                    x, y, w, h = [int(v) for v in bbox]
                    current_area = w * h
                    size_history.append(current_area)

                    # Keep only last 30 frames
                    if len(size_history) > 30:
                        size_history.pop(0)

                    # Save coordinates
                    self.coords_dict[self.current_frame] = (self.current_frame, x, y, w, h)
                    self.current_bbox = (x, y, w, h)
                    last_tracked_frame = self.current_frame

                    # Detect problems
                    area_ratio = current_area / initial_area
                    recent_avg_area = sum(size_history) / len(size_history)
                    size_change = abs(current_area - recent_avg_area) / recent_avg_area if recent_avg_area > 0 else 0

                    # Determine color based on tracking quality
                    color = 'green'
                    status = "Tracking OK"

                    if area_ratio < 0.3:
                        color = 'red'
                        status = "WARNING: Box too small!"
                    elif area_ratio < 0.5:
                        color = 'orange'
                        status = "ATTENTION: Box shrinking"
                    elif size_change > 0.2:
                        color = 'orange'
                        status = "ATTENTION: Sudden change"

                    # Emit progress (always emit progress_update for progress bar)
                    self.progress_update.emit(self.current_frame, self.total_frames, status)

                    # Throttle UI updates: only emit frame_tracked every N frames
                    frames_since_ui_update += 1
                    if frames_since_ui_update >= ui_update_interval:
                        self.frame_tracked.emit(self.current_frame, (x, y, w, h), color)
                        frames_since_ui_update = 0

                else:
                    # Tracking lost - always show immediately
                    self.frame_tracked.emit(self.current_frame, None, 'red')
                    self.progress_update.emit(self.current_frame, self.total_frames, "TRACKING LOST!")

                    # Pause and wait for user to reinitialize
                    self.is_paused = True
                    frames_since_ui_update = 0

                # Move to next frame
                self.current_frame += 1

                # Small delay to not overwhelm the UI
                time.sleep(0.001)

            # Save to CSV
            if self.coords_dict and not self.should_stop:
                self.tracking_complete.emit(self.coords_dict)
            else:
                self.tracking_error.emit("Tracking stopped by user")

        except Exception as e:
            self.tracking_error.emit(f"Tracking error: {str(e)}")

        finally:
            if self.cap:
                self.cap.release()
            self.is_running = False

    def _create_tracker(self, tracker_type):
        """Create OpenCV tracker based on type"""
        try:
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
        except Exception as e:
            print(f"Error creating tracker: {e}")
            return None

    def save_to_csv(self, output_path):
        """Save tracking coordinates to CSV file"""
        try:
            # Sort frames
            sorted_frames = sorted(self.coords_dict.keys())

            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['frame', 'x', 'y', 'w', 'h'])

                for frame_num in sorted_frames:
                    frame, x, y, w, h = self.coords_dict[frame_num]
                    writer.writerow([frame, x, y, w, h])

            return True
        except Exception as e:
            print(f"Error saving CSV: {e}")
            return False
