"""
Tracking Thread YOLO for Dancer Tracking UI
Runs YOLOv8 tracking in background without blocking the UI
Compatible with the existing UI architecture
"""

import cv2
import time
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from ultralytics import YOLO


class TrackingThreadYOLO(QThread):
    """Thread for running YOLO tracking in background"""

    # Signals to communicate with UI (compatible with existing TrackingThread)
    progress_update = pyqtSignal(int, int, str)  # frame, total_frames, status_text
    frame_tracked = pyqtSignal(int, object, str, object)  # frame_number, bbox (x,y,w,h) or None, color, frame_cv
    tracking_complete = pyqtSignal(dict)  # coords_dict
    tracking_error = pyqtSignal(str)  # error_message

    def __init__(self, video_path, model_size="n", tracker_type="botsort", conf_threshold=0.3, start_frame=0):
        """
        Initialize YOLO tracking thread

        Args:
            video_path: Path to video file
            model_size: YOLO model size (n, s, m, l, x) - 'n' recommended for CPU
            tracker_type: Tracker type ('botsort' or 'bytetrack')
            conf_threshold: Confidence threshold for detections (0.0-1.0)
            start_frame: Starting frame number
        """
        super().__init__()
        self.video_path = video_path
        self.model_size = model_size
        self.tracker_type = tracker_type
        self.conf_threshold = conf_threshold
        self.start_frame = start_frame

        # Control flags
        self.is_running = False
        self.should_stop = False

        # Video info (loaded in run())
        self.cap = None
        self.fps = 0
        self.frame_count = 0
        self.width = 0
        self.height = 0

        # YOLO model (loaded in run())
        self.model = None

        # Tracking results
        self.coords_dict = {}  # {frame_num: (frame_num, x, y, w, h)} for compatibility
        self.coords_dict_detailed = {}  # {frame_num: {track_id: (x, y, w, h, conf)}}

    def stop(self):
        """Stop tracking"""
        self.should_stop = True

    def run(self):
        """Main tracking loop"""
        try:
            self.is_running = True
            self.should_stop = False

            # Load video info
            if not self._load_video_info():
                self.tracking_error.emit("Cannot open video file")
                return

            # Load YOLO model
            if not self._load_model():
                self.tracking_error.emit(f"Failed to load YOLO model yolov8{self.model_size}.pt")
                return

            # Emit initial status
            self.progress_update.emit(0, self.frame_count, "Initializing YOLO tracking...")

            # Run YOLO tracking (streams results frame by frame)
            self._run_tracking()

            # Complete tracking
            if self.coords_dict and not self.should_stop:
                self.tracking_complete.emit(self.coords_dict)
            else:
                self.tracking_error.emit("Tracking stopped by user")

        except Exception as e:
            import traceback
            self.tracking_error.emit(f"Tracking error: {str(e)}\n{traceback.format_exc()}")

        finally:
            self.is_running = False

    def _load_video_info(self):
        """Load video information"""
        try:
            self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                return False

            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.cap.release()

            return True
        except Exception as e:
            print(f"Error loading video info: {e}")
            return False

    def _load_model(self):
        """Load YOLO model"""
        try:
            model_name = f"yolov8{self.model_size}.pt"
            print(f"Loading {model_name}...")
            self.model = YOLO(model_name)
            return True
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            return False

    def _run_tracking(self):
        """Run YOLO tracking on video"""
        print("\nStarting YOLO tracking...")
        print(f"  Video: {self.width}x{self.height} @ {self.fps} FPS")
        print(f"  Frames: {self.frame_count}")
        print(f"  Tracker: {self.tracker_type.upper()}")
        print(f"  Confidence: {self.conf_threshold}")

        # Open video for reading frames
        cap = cv2.VideoCapture(self.video_path)

        # Skip to start frame if needed
        if self.start_frame > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)

        # Run YOLO tracking with streaming
        results = self.model.track(
            source=self.video_path,
            tracker=f"{self.tracker_type}.yaml",
            device="cpu",
            classes=[0],  # Only persons
            persist=True,  # Maintain IDs between frames
            conf=self.conf_threshold,
            verbose=False,
            stream=True  # Stream results frame by frame
        )

        frame_num = self.start_frame

        for result in results:
            if self.should_stop:
                break

            # Read the corresponding frame from video for display
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ok, frame = cap.read()
            if not ok:
                break

            boxes = result.boxes

            # Process detections
            frame_detections = {}
            combined_bbox = None

            if boxes is not None and len(boxes) > 0:
                # Collect all detections for this frame
                all_boxes = []

                for box in boxes:
                    # Extract information
                    track_id = int(box.id[0]) if box.id is not None else -1
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0])

                    # Convert to (x, y, w, h) format
                    x, y = int(x1), int(y1)
                    w, h = int(x2 - x1), int(y2 - y1)

                    frame_detections[track_id] = (x, y, w, h, conf)
                    all_boxes.append([x, y, x+w, y+h])

                # Calculate combined bbox that encompasses all dancers
                if len(all_boxes) > 0:
                    all_boxes = np.array(all_boxes)
                    x_min = int(all_boxes[:, 0].min())
                    y_min = int(all_boxes[:, 1].min())
                    x_max = int(all_boxes[:, 2].max())
                    y_max = int(all_boxes[:, 3].max())

                    w_combined = x_max - x_min
                    h_combined = y_max - y_min

                    combined_bbox = (x_min, y_min, w_combined, h_combined)

                    # Store in coords_dict (compatible format with existing code)
                    self.coords_dict[frame_num] = (frame_num, x_min, y_min, w_combined, h_combined)

                    # Store detailed detections
                    self.coords_dict_detailed[frame_num] = frame_detections

            # Determine color based on detection quality
            if combined_bbox:
                # Green if we have good detections
                color = 'green'
                bbox_to_show = combined_bbox
                status = f"Tracking: {len(frame_detections)} person(s)"
            else:
                # No detections in this frame
                color = 'gray'
                bbox_to_show = None
                status = "No detections"

            # Draw bounding boxes on frame (show individual dancers with their IDs)
            frame_display = frame.copy()
            if combined_bbox:
                # Draw individual dancer boxes
                colors_by_id = {
                    0: (0, 255, 0),    # Green
                    1: (255, 0, 0),    # Blue
                    2: (0, 0, 255),    # Red
                    3: (255, 255, 0),  # Cyan
                    4: (255, 0, 255),  # Magenta
                    5: (0, 255, 255),  # Yellow
                }

                for track_id, (x, y, w, h, conf) in frame_detections.items():
                    box_color = colors_by_id.get(track_id, (255, 255, 255))

                    # Draw bbox
                    cv2.rectangle(frame_display, (x, y), (x+w, y+h), box_color, 2)

                    # Label with ID and confidence
                    label = f"ID:{track_id} ({conf:.2f})"
                    cv2.putText(frame_display, label, (x, y-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)

                # Draw combined bbox (in white)
                x_min, y_min, w_combined, h_combined = combined_bbox
                cv2.rectangle(frame_display, (x_min, y_min), (x_min+w_combined, y_min+h_combined),
                             (255, 255, 255), 2)

            # Emit frame for display
            frame_copy = frame_display.copy()
            self.frame_tracked.emit(frame_num, bbox_to_show, color, frame_copy)

            # Update progress
            self.progress_update.emit(frame_num, self.frame_count, status)

            frame_num += 1

            # Small delay to not overwhelm UI
            time.sleep(0.001)

        cap.release()

        # Print statistics
        self._print_statistics()

    def _print_statistics(self):
        """Print tracking statistics"""
        total_frames_with_detections = len(self.coords_dict)
        total_detections = sum(len(dets) for dets in self.coords_dict_detailed.values())

        # Count unique IDs
        all_ids = set()
        for frame_dets in self.coords_dict_detailed.values():
            for track_id in frame_dets.keys():
                if track_id != -1:
                    all_ids.add(track_id)

        print("\nTracking statistics:")
        print(f"  - Frames with detections: {total_frames_with_detections}/{self.frame_count}")
        print(f"  - Total detections: {total_detections}")
        if total_frames_with_detections > 0:
            print(f"  - Average detections/frame: {total_detections/total_frames_with_detections:.2f}")
        print(f"  - Unique IDs detected: {len(all_ids)}")
        if len(all_ids) > 0:
            print(f"  - IDs: {sorted(all_ids)}")

    def save_to_csv(self, output_path):
        """Save tracking coordinates to CSV file (compatible format)"""
        if not self.coords_dict:
            return False

        try:
            import csv
            sorted_frames = sorted(self.coords_dict.keys())
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['frame', 'x', 'y', 'w', 'h'])

                for frame_num in sorted_frames:
                    frame, x, y, w, h = self.coords_dict[frame_num]
                    writer.writerow([frame, x, y, w, h])

            print(f"Saved coordinates to {output_path}")
            return True
        except Exception as e:
            print(f"Error saving CSV: {e}")
            return False

    def save_detailed_csv(self, output_path):
        """Save detailed coordinates with track IDs"""
        if not self.coords_dict_detailed:
            return False

        try:
            import csv
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['frame', 'track_id', 'x', 'y', 'w', 'h', 'conf'])

                for frame_num in sorted(self.coords_dict_detailed.keys()):
                    detections = self.coords_dict_detailed[frame_num]
                    for track_id, (x, y, w, h, conf) in detections.items():
                        writer.writerow([frame_num, track_id, x, y, w, h, f"{conf:.3f}"])

            print(f"Saved detailed coordinates to {output_path}")
            return True
        except Exception as e:
            print(f"Error saving detailed CSV: {e}")
            return False

    # Compatibility methods with TrackingThread interface
    def pause(self):
        """Pause tracking - YOLO doesn't support pausing during processing"""
        pass  # Not applicable for YOLO batch processing

    def resume(self):
        """Resume tracking - YOLO doesn't support pausing during processing"""
        pass  # Not applicable for YOLO batch processing

    def request_reinitialize(self):
        """Request tracker reinitialization - YOLO doesn't need manual reinit"""
        pass  # YOLO re-detects automatically

    def handle_key(self, key):
        """Forward keyboard event - not needed for YOLO"""
        pass  # YOLO doesn't require manual intervention

    def set_current_frame(self, frame_number):
        """Update current frame position - not applicable during YOLO processing"""
        pass  # YOLO processes sequentially

    @property
    def is_paused(self):
        """Check if tracking is paused - YOLO is never paused"""
        return False

    @property
    def current_frame(self):
        """Get current frame number"""
        return len(self.coords_dict)

    @property
    def total_frames(self):
        """Get total frame count"""
        return self.frame_count
