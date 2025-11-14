"""
Video Player Widget for Dancer Tracking UI
Handles video playback, display, and tracking visualization
"""

import cv2
import numpy as np
from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont


class VideoPlayer(QWidget):
    """Custom video player widget with OpenCV backend"""

    # Signals
    frame_changed = pyqtSignal(int)  # Emits current frame number
    bbox_selected = pyqtSignal(tuple)  # Emits (x, y, w, h) when user selects bbox

    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_path = None
        self.cap = None
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 30
        self.is_playing = False
        self.playback_speed = 1.0

        # Tracking visualization
        self.bbox = None  # (x, y, w, h)
        self.bbox_color = QColor(0, 255, 0)  # Green by default

        # Selection mode
        self.selection_mode = False
        self.selection_start = None
        self.selection_end = None

        # Cache for current frame
        self.current_image = None

        # UI Setup
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black;")
        self.video_label.setMinimumSize(640, 480)

        # Timer for playback
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance_frame)

        # Enable mouse tracking for bbox selection
        self.video_label.setMouseTracking(True)
        self.video_label.mousePressEvent = self._mouse_press
        self.video_label.mouseMoveEvent = self._mouse_move
        self.video_label.mouseReleaseEvent = self._mouse_release

        # Layout
        from PyQt5.QtWidgets import QVBoxLayout
        layout = QVBoxLayout(self)
        layout.addWidget(self.video_label)
        layout.setContentsMargins(0, 0, 0, 0)

    def load_video(self, video_path):
        """Load video file"""
        self.video_path = video_path

        # Release previous video if any
        if self.cap:
            self.cap.release()

        self.cap = cv2.VideoCapture(video_path)

        if not self.cap.isOpened():
            return False

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.current_frame = 0

        # Show first frame
        self.seek_frame(0)
        return True

    def get_video_info(self):
        """Return video information as dict"""
        if not self.cap:
            return None

        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = self.total_frames / self.fps if self.fps > 0 else 0

        return {
            'width': width,
            'height': height,
            'fps': self.fps,
            'total_frames': self.total_frames,
            'duration': duration
        }

    def play(self):
        """Start video playback"""
        if self.cap and not self.is_playing:
            self.is_playing = True
            interval = int(1000 / (self.fps * self.playback_speed))
            self.timer.start(interval)

    def pause(self):
        """Pause video playback"""
        if self.is_playing:
            self.is_playing = False
            self.timer.stop()

    def toggle_play_pause(self):
        """Toggle between play and pause"""
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def set_playback_speed(self, speed):
        """Set playback speed (0.25x, 0.5x, 1x, 2x, etc.)"""
        self.playback_speed = speed
        if self.is_playing:
            self.pause()
            self.play()

    def seek_frame(self, frame_number):
        """Seek to specific frame"""
        if not self.cap:
            return False

        frame_number = max(0, min(frame_number, self.total_frames - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self.current_frame = frame_number

        ret, frame = self.cap.read()
        if ret:
            self._display_frame(frame)
            self.frame_changed.emit(self.current_frame)
            return True
        return False

    def seek_time(self, seconds):
        """Seek to specific time in seconds"""
        if not self.cap or self.fps == 0:
            return False

        frame_number = int(seconds * self.fps)
        return self.seek_frame(frame_number)

    def next_frame(self):
        """Advance one frame"""
        return self.seek_frame(self.current_frame + 1)

    def prev_frame(self):
        """Go back one frame"""
        return self.seek_frame(self.current_frame - 1)

    def skip_seconds(self, seconds):
        """Skip forward or backward by seconds"""
        current_time = self.current_frame / self.fps if self.fps > 0 else 0
        return self.seek_time(current_time + seconds)

    def set_bbox(self, bbox, color='green'):
        """Set bounding box to display (x, y, w, h)"""
        self.bbox = bbox

        # Set color based on tracking state
        color_map = {
            'green': QColor(0, 255, 0),
            'orange': QColor(255, 165, 0),
            'red': QColor(255, 0, 0),
            'blue': QColor(0, 120, 255)
        }
        self.bbox_color = color_map.get(color, QColor(0, 255, 0))

        # Just redraw cached frame without seeking (prevents recursive seek and file contention)
        if self.current_image is not None:
            self._display_frame(self.current_image)

    def clear_bbox(self):
        """Clear bounding box"""
        self.bbox = None
        # Just redraw cached frame without seeking (prevents recursive seek and file contention)
        if self.current_image is not None:
            self._display_frame(self.current_image)

    def start_selection(self):
        """Enable bbox selection mode"""
        self.selection_mode = True
        self.selection_start = None
        self.selection_end = None
        self.video_label.setCursor(Qt.CrossCursor)

    def stop_selection(self):
        """Disable bbox selection mode"""
        self.selection_mode = False
        self.selection_start = None
        self.selection_end = None
        self.video_label.setCursor(Qt.ArrowCursor)

    def _advance_frame(self):
        """Internal method to advance frame during playback"""
        if self.current_frame >= self.total_frames - 1:
            self.pause()
            return

        self.current_frame += 1
        ret, frame = self.cap.read()

        if ret:
            self._display_frame(frame)
            self.frame_changed.emit(self.current_frame)
        else:
            self.pause()

    def _display_frame(self, frame):
        """Display frame with overlays"""
        if frame is None:
            return

        # Store original frame
        display_frame = frame.copy()

        # Draw bounding box if present
        if self.bbox:
            x, y, w, h = [int(v) for v in self.bbox]
            cv2.rectangle(display_frame, (x, y), (x + w, y + h),
                         (self.bbox_color.blue(), self.bbox_color.green(), self.bbox_color.red()), 3)

            # Draw coordinates text
            coord_text = f"({x}, {y}) {w}x{h}"
            cv2.putText(display_frame, coord_text, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                       (self.bbox_color.blue(), self.bbox_color.green(), self.bbox_color.red()), 2)

        # Draw selection rectangle if in selection mode
        if self.selection_mode and self.selection_start and self.selection_end:
            start_x, start_y = self.selection_start
            end_x, end_y = self.selection_end
            cv2.rectangle(display_frame, (start_x, start_y), (end_x, end_y),
                         (255, 255, 0), 2)  # Yellow

        # Draw frame info overlay
        current_time = self.current_frame / self.fps if self.fps > 0 else 0
        info_text = f"Frame: {self.current_frame}/{self.total_frames} | Time: {current_time:.2f}s"
        cv2.putText(display_frame, info_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Convert to QImage
        height, width, channel = display_frame.shape
        bytes_per_line = 3 * width
        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        q_image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)

        # Scale to fit label while maintaining aspect ratio
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.video_label.setPixmap(scaled_pixmap)
        self.current_image = display_frame

    def _mouse_press(self, event):
        """Handle mouse press for bbox selection"""
        if not self.selection_mode:
            return

        # Convert widget coordinates to video coordinates
        pos = self._widget_to_video_coords(event.pos())
        if pos:
            self.selection_start = pos
            self.selection_end = pos

    def _mouse_move(self, event):
        """Handle mouse move for bbox selection"""
        if not self.selection_mode or not self.selection_start:
            return

        pos = self._widget_to_video_coords(event.pos())
        if pos:
            self.selection_end = pos
            # Redraw with selection rectangle
            self.seek_frame(self.current_frame)

    def _mouse_release(self, event):
        """Handle mouse release for bbox selection"""
        if not self.selection_mode or not self.selection_start:
            return

        pos = self._widget_to_video_coords(event.pos())
        if pos:
            self.selection_end = pos

            # Calculate bbox
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end

            x = min(x1, x2)
            y = min(y1, y2)
            w = abs(x2 - x1)
            h = abs(y2 - y1)

            # Only emit if bbox is large enough
            if w > 10 and h > 10:
                self.bbox_selected.emit((x, y, w, h))

            # Reset selection
            self.selection_start = None
            self.selection_end = None
            self.stop_selection()

    def _widget_to_video_coords(self, widget_pos):
        """Convert widget coordinates to video frame coordinates"""
        if not self.current_image is not None:
            return None

        pixmap = self.video_label.pixmap()
        if not pixmap:
            return None

        # Get video dimensions
        video_height, video_width = self.current_image.shape[:2]

        # Get displayed pixmap size
        pixmap_width = pixmap.width()
        pixmap_height = pixmap.height()

        # Get label size
        label_width = self.video_label.width()
        label_height = self.video_label.height()

        # Calculate offset (pixmap is centered in label)
        x_offset = (label_width - pixmap_width) / 2
        y_offset = (label_height - pixmap_height) / 2

        # Convert to pixmap coordinates
        pixmap_x = widget_pos.x() - x_offset
        pixmap_y = widget_pos.y() - y_offset

        # Check if click is within pixmap
        if pixmap_x < 0 or pixmap_x >= pixmap_width or pixmap_y < 0 or pixmap_y >= pixmap_height:
            return None

        # Scale to video coordinates
        scale_x = video_width / pixmap_width
        scale_y = video_height / pixmap_height

        video_x = int(pixmap_x * scale_x)
        video_y = int(pixmap_y * scale_y)

        return (video_x, video_y)

    def get_current_frame_image(self):
        """Return current frame as numpy array"""
        return self.current_image

    def closeEvent(self, event):
        """Cleanup when widget is closed"""
        if self.cap:
            self.cap.release()
        self.timer.stop()
        super().closeEvent(event)
