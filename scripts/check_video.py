#!/usr/bin/env python3
"""
Script pour vérifier si une vidéo peut être lue par OpenCV
"""

import cv2
import sys
import os

def check_video(video_path):
    """Vérifie si une vidéo peut être lue correctement"""

    if not os.path.exists(video_path):
        print(f"ERROR: Video file not found: {video_path}")
        return False

    print(f"Checking video: {video_path}")
    print(f"File size: {os.path.getsize(video_path) / (1024*1024):.1f} MB")
    print()

    # Ouvrir la vidéo
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("ERROR: Cannot open video file")
        print("Possible reasons:")
        print("  - Codec not supported by OpenCV")
        print("  - File is corrupted")
        print("  - File format not recognized")
        return False

    # Obtenir les propriétés
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))

    print("Video properties:")
    print(f"  Resolution: {width}x{height}")
    print(f"  FPS: {fps:.2f}")
    print(f"  Total frames: {total_frames}")
    print(f"  Duration: {total_frames/fps:.1f} seconds")
    print(f"  Codec (FourCC): {fourcc}")
    print()

    # Essayer de lire quelques frames
    print("Testing frame reading...")
    frames_read = 0
    frames_to_test = min(10, total_frames)

    for i in range(frames_to_test):
        ret, frame = cap.read()
        if ret and frame is not None and frame.size > 0:
            frames_read += 1
            if i == 0:
                print(f"  Frame 0: OK (shape: {frame.shape})")
        else:
            print(f"  Frame {i}: FAILED")
            break

    cap.release()

    print(f"\nFrames successfully read: {frames_read}/{frames_to_test}")

    if frames_read == 0:
        print("\nERROR: Cannot read any frames from the video!")
        print("\nSOLUTION: You need to convert the video to a compatible format")
        print("Use this command (requires ffmpeg):")
        print(f'  ffmpeg -i "{video_path}" -c:v libx264 -preset fast -crf 18 -c:a aac "video_converted.mp4"')
        return False
    elif frames_read < frames_to_test:
        print("\nWARNING: Some frames could not be read")
        return False
    else:
        print("\nSUCCESS: Video can be read correctly by OpenCV!")
        return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_video.py <video_path>")
        sys.exit(1)

    video_path = sys.argv[1]
    success = check_video(video_path)
    sys.exit(0 if success else 1)
