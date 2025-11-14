"""
Quick test to verify UI modules can be imported
"""

import sys

print("Testing imports...")

try:
    print("  - Importing video_player...")
    from video_player import VideoPlayer
    print("    OK")
except Exception as e:
    print(f"    ERROR: {e}")
    sys.exit(1)

try:
    print("  - Importing timeline_widget...")
    from timeline_widget import TimelineWidget
    print("    OK")
except Exception as e:
    print(f"    ERROR: {e}")
    sys.exit(1)

try:
    print("  - Importing tracking_thread...")
    from tracking_thread import TrackingThread
    print("    OK")
except Exception as e:
    print(f"    ERROR: {e}")
    sys.exit(1)

try:
    print("  - Importing export_thread...")
    from export_thread import ExportThread
    print("    OK")
except Exception as e:
    print(f"    ERROR: {e}")
    sys.exit(1)

try:
    print("  - Importing dancer_tracking_ui...")
    from dancer_tracking_ui import DancerTrackingUI
    print("    OK")
except Exception as e:
    print(f"    ERROR: {e}")
    sys.exit(1)

print("\nAll imports successful!")
print("\nTo run the UI, execute: python dancer_tracking_ui.py")
print("Or simply double-click: start_ui.bat")
