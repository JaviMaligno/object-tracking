"""
Timeline Widget for Dancer Tracking UI
Visual representation of tracking status across video frames
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QRect
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush


class TimelineWidget(QWidget):
    """Custom timeline widget showing tracking status per frame"""

    # Signals
    frame_clicked = pyqtSignal(int)  # Emits frame number when clicked

    # Frame states
    STATE_UNTRACKED = 0  # No tracking data
    STATE_TRACKED = 1    # Successfully tracked
    STATE_INTERPOLATED = 2  # Interpolated (filled gap)
    STATE_PROBLEM = 3    # Problem detected

    def __init__(self, parent=None):
        super().__init__(parent)
        self.total_frames = 0
        self.current_frame = 0
        self.frame_states = []  # List of states for each frame

        # Colors
        self.colors = {
            self.STATE_UNTRACKED: QColor(60, 60, 60),      # Dark gray
            self.STATE_TRACKED: QColor(0, 200, 0),         # Green
            self.STATE_INTERPOLATED: QColor(255, 200, 0),  # Yellow
            self.STATE_PROBLEM: QColor(255, 50, 50),       # Red
            'current': QColor(0, 120, 255),                # Blue
            'background': QColor(30, 30, 30),              # Background
            'text': QColor(200, 200, 200)                  # Text
        }

        # View settings
        self.zoom_level = 1.0
        self.scroll_offset = 0
        self.pixels_per_frame = 2  # Can be adjusted with zoom

        self.setMinimumHeight(60)
        self.setMouseTracking(True)

        # Tooltip
        self.setToolTip("Click to jump to frame")

    def set_total_frames(self, total_frames):
        """Initialize timeline with total number of frames"""
        self.total_frames = total_frames
        self.frame_states = [self.STATE_UNTRACKED] * total_frames
        self.current_frame = 0
        self.update()

    def set_current_frame(self, frame_number):
        """Update current frame position"""
        if 0 <= frame_number < self.total_frames:
            self.current_frame = frame_number
            self.update()

            # Auto-scroll to keep current frame visible
            self._auto_scroll_to_frame(frame_number)

    def set_frame_state(self, frame_number, state):
        """Set state for a specific frame"""
        if 0 <= frame_number < self.total_frames:
            self.frame_states[frame_number] = state
            self.update()

    def set_frame_states_bulk(self, start_frame, end_frame, state):
        """Set state for a range of frames"""
        for frame in range(start_frame, min(end_frame + 1, self.total_frames)):
            if 0 <= frame < self.total_frames:
                self.frame_states[frame] = state
        self.update()

    def clear_states(self):
        """Reset all frame states to untracked"""
        self.frame_states = [self.STATE_UNTRACKED] * self.total_frames
        self.update()

    def set_zoom(self, zoom_level):
        """Set zoom level (0.5 = zoom out, 2.0 = zoom in)"""
        self.zoom_level = max(0.1, min(zoom_level, 10.0))
        self.pixels_per_frame = max(1, int(2 * self.zoom_level))
        self.update()

    def zoom_in(self):
        """Zoom in"""
        self.set_zoom(self.zoom_level * 1.5)

    def zoom_out(self):
        """Zoom out"""
        self.set_zoom(self.zoom_level / 1.5)

    def paintEvent(self, event):
        """Draw the timeline"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.fillRect(self.rect(), self.colors['background'])

        if self.total_frames == 0:
            # Draw placeholder text
            painter.setPen(self.colors['text'])
            painter.drawText(self.rect(), Qt.AlignCenter, "No video loaded")
            return

        # Calculate dimensions
        width = self.width()
        height = self.height()
        timeline_height = height - 20  # Leave space for labels
        timeline_y = 10

        # Calculate visible range
        visible_frames = int(width / self.pixels_per_frame)
        start_frame = max(0, self.scroll_offset)
        end_frame = min(self.total_frames, start_frame + visible_frames)

        # Draw frame states
        for frame in range(start_frame, end_frame):
            x = (frame - start_frame) * self.pixels_per_frame
            if x >= width:
                break

            state = self.frame_states[frame]
            color = self.colors[state]

            # Draw frame bar
            painter.fillRect(int(x), timeline_y, max(1, self.pixels_per_frame - 1), timeline_height, color)

        # Draw current frame indicator
        if start_frame <= self.current_frame < end_frame:
            current_x = (self.current_frame - start_frame) * self.pixels_per_frame
            painter.setPen(QPen(self.colors['current'], 2))
            painter.drawLine(int(current_x), 0, int(current_x), height)

            # Draw frame number
            painter.setPen(self.colors['text'])
            text = f"Frame {self.current_frame}"
            text_x = max(5, min(int(current_x) - 30, width - 80))
            painter.drawText(text_x, height - 5, text)

        # Draw time markers
        if self.pixels_per_frame >= 1:
            painter.setPen(self.colors['text'])
            # Draw marker every ~100 pixels
            marker_interval = max(1, int(100 / self.pixels_per_frame))
            for frame in range(start_frame, end_frame, marker_interval):
                x = (frame - start_frame) * self.pixels_per_frame
                if x >= width - 40:
                    break
                painter.drawText(int(x), 10, f"{frame}")

    def mousePressEvent(self, event):
        """Handle mouse click to jump to frame"""
        if event.button() == Qt.LeftButton and self.total_frames > 0:
            # Calculate clicked frame
            visible_frames = int(self.width() / self.pixels_per_frame)
            start_frame = max(0, self.scroll_offset)

            click_x = event.pos().x()
            frame_offset = int(click_x / self.pixels_per_frame)
            clicked_frame = start_frame + frame_offset

            if 0 <= clicked_frame < self.total_frames:
                self.frame_clicked.emit(clicked_frame)

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def _auto_scroll_to_frame(self, frame_number):
        """Auto-scroll timeline to keep frame visible"""
        visible_frames = int(self.width() / self.pixels_per_frame)

        # Check if frame is outside visible range
        if frame_number < self.scroll_offset:
            self.scroll_offset = frame_number
        elif frame_number >= self.scroll_offset + visible_frames:
            self.scroll_offset = frame_number - visible_frames + 1

        self.scroll_offset = max(0, min(self.scroll_offset, self.total_frames - visible_frames))

    def get_statistics(self):
        """Return statistics about tracking states"""
        if not self.frame_states:
            return {}

        total = len(self.frame_states)
        tracked = self.frame_states.count(self.STATE_TRACKED)
        interpolated = self.frame_states.count(self.STATE_INTERPOLATED)
        untracked = self.frame_states.count(self.STATE_UNTRACKED)
        problem = self.frame_states.count(self.STATE_PROBLEM)

        return {
            'total': total,
            'tracked': tracked,
            'interpolated': interpolated,
            'untracked': untracked,
            'problem': problem,
            'tracked_percent': (tracked / total * 100) if total > 0 else 0,
            'coverage_percent': ((tracked + interpolated) / total * 100) if total > 0 else 0
        }

    def find_gaps(self):
        """Find gaps (continuous ranges of untracked frames)"""
        gaps = []
        in_gap = False
        gap_start = 0

        for i, state in enumerate(self.frame_states):
            if state == self.STATE_UNTRACKED:
                if not in_gap:
                    in_gap = True
                    gap_start = i
            else:
                if in_gap:
                    gaps.append((gap_start, i - 1))
                    in_gap = False

        # Close last gap if needed
        if in_gap:
            gaps.append((gap_start, len(self.frame_states) - 1))

        return gaps
