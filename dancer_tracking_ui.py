"""
Dancer Tracking UI - Interfaz gráfica completa
Aplicación tipo editor de video para tracking de bailarines
"""

import sys
import os
import csv
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QComboBox, QLineEdit, QCheckBox,
    QFileDialog, QMessageBox, QProgressBar, QTextEdit, QGroupBox,
    QSpinBox, QDoubleSpinBox, QSplitter, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon

# Import custom widgets and threads
from video_player import VideoPlayer
from timeline_widget import TimelineWidget
from tracking_thread import TrackingThread
from export_thread import ExportThread


class DancerTrackingUI(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dancer Tracking - Video Editor")
        self.setGeometry(100, 100, 1400, 900)

        # Application state
        self.video_path = None
        self.audio_path = None
        self.coords_csv = "coords.csv"
        self.tracking_thread = None
        self.export_thread = None
        self.tracking_active = False
        self.last_resume_frame = None  # Track last frame where we resumed to avoid re-init

        # Setup UI
        self._setup_ui()

        # Check for existing coords
        self._check_existing_coords()

    def _setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # Left panel: Video player and timeline
        left_panel = QVBoxLayout()

        # Top section: File selection
        file_section = self._create_file_section()
        left_panel.addWidget(file_section)

        # Video player
        self.video_player = VideoPlayer()
        self.video_player.frame_changed.connect(self._on_frame_changed)
        self.video_player.bbox_selected.connect(self._on_bbox_selected)
        left_panel.addWidget(self.video_player, stretch=1)

        # Playback controls
        controls_section = self._create_playback_controls()
        left_panel.addWidget(controls_section)

        # Timeline
        timeline_section = self._create_timeline_section()
        left_panel.addWidget(timeline_section)

        # Right panel: Configuration and controls
        right_panel = QVBoxLayout()

        # Tracking configuration
        tracking_section = self._create_tracking_section()
        right_panel.addWidget(tracking_section)

        # Export configuration
        export_section = self._create_export_section()
        right_panel.addWidget(export_section)

        # Log/Status
        log_section = self._create_log_section()
        right_panel.addWidget(log_section)

        right_panel.addStretch()

        # Add panels to main layout
        main_layout.addLayout(left_panel, stretch=3)
        main_layout.addLayout(right_panel, stretch=1)

        # Apply stylesheet
        self._apply_stylesheet()

    def _create_file_section(self):
        """Create file selection section"""
        group = QGroupBox("1. Cargar Video")
        layout = QVBoxLayout()

        # Video file
        video_layout = QHBoxLayout()
        self.video_path_label = QLabel("No hay video cargado")
        self.video_path_label.setWordWrap(True)
        video_btn = QPushButton("Abrir Video...")
        video_btn.clicked.connect(self._open_video)
        video_layout.addWidget(self.video_path_label, stretch=1)
        video_layout.addWidget(video_btn)
        layout.addLayout(video_layout)

        # Audio file (optional)
        audio_layout = QHBoxLayout()
        self.audio_path_label = QLabel("Audio: usar del video")
        self.audio_path_label.setWordWrap(True)
        audio_btn = QPushButton("Cambiar Audio... (opcional)")
        audio_btn.clicked.connect(self._open_audio)
        audio_layout.addWidget(self.audio_path_label, stretch=1)
        audio_layout.addWidget(audio_btn)
        layout.addLayout(audio_layout)

        # Video info
        self.video_info_label = QLabel("")
        self.video_info_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.video_info_label)

        # Use existing coords
        self.use_existing_checkbox = QCheckBox("Usar coordenadas existentes (coords.csv)")
        self.use_existing_checkbox.setEnabled(False)
        self.use_existing_checkbox.stateChanged.connect(self._on_use_existing_changed)
        layout.addWidget(self.use_existing_checkbox)

        group.setLayout(layout)
        return group

    def _create_playback_controls(self):
        """Create playback control buttons"""
        group = QGroupBox("Controles de Reproducción")
        layout = QVBoxLayout()

        # Main controls
        main_controls = QHBoxLayout()

        self.play_pause_btn = QPushButton("▶ Play / Pause")
        self.play_pause_btn.clicked.connect(self._toggle_play_pause)
        self.play_pause_btn.setEnabled(False)
        main_controls.addWidget(self.play_pause_btn)

        layout.addLayout(main_controls)

        # Speed control
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Velocidad:"))

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "1x", "2x"])
        self.speed_combo.setCurrentText("1x")
        self.speed_combo.currentTextChanged.connect(self._on_speed_changed)
        speed_layout.addWidget(self.speed_combo)

        speed_layout.addStretch()
        layout.addLayout(speed_layout)

        # Frame navigation buttons
        frame_nav_layout = QHBoxLayout()
        frame_nav_layout.addWidget(QLabel("Frames:"))

        btn_back_10f = QPushButton("◀◀ 10f")
        btn_back_10f.clicked.connect(lambda: self.video_player.seek_frame(self.video_player.current_frame - 10))
        btn_back_10f.setEnabled(False)
        frame_nav_layout.addWidget(btn_back_10f)

        btn_back_1f = QPushButton("◀ 1f")
        btn_back_1f.clicked.connect(self.video_player.prev_frame)
        btn_back_1f.setEnabled(False)
        frame_nav_layout.addWidget(btn_back_1f)

        btn_forward_1f = QPushButton("1f ▶")
        btn_forward_1f.clicked.connect(self.video_player.next_frame)
        btn_forward_1f.setEnabled(False)
        frame_nav_layout.addWidget(btn_forward_1f)

        btn_forward_10f = QPushButton("10f ▶▶")
        btn_forward_10f.clicked.connect(lambda: self.video_player.seek_frame(self.video_player.current_frame + 10))
        btn_forward_10f.setEnabled(False)
        frame_nav_layout.addWidget(btn_forward_10f)

        layout.addLayout(frame_nav_layout)

        # Time navigation buttons
        time_nav_layout = QHBoxLayout()
        time_nav_layout.addWidget(QLabel("Tiempo:"))

        btn_back_5s = QPushButton("◀◀ 5s")
        btn_back_5s.clicked.connect(lambda: self.video_player.skip_seconds(-5))
        btn_back_5s.setEnabled(False)
        time_nav_layout.addWidget(btn_back_5s)

        btn_back_1s = QPushButton("◀ 1s")
        btn_back_1s.clicked.connect(lambda: self.video_player.skip_seconds(-1))
        btn_back_1s.setEnabled(False)
        time_nav_layout.addWidget(btn_back_1s)

        btn_forward_1s = QPushButton("1s ▶")
        btn_forward_1s.clicked.connect(lambda: self.video_player.skip_seconds(1))
        btn_forward_1s.setEnabled(False)
        time_nav_layout.addWidget(btn_forward_1s)

        btn_forward_5s = QPushButton("5s ▶▶")
        btn_forward_5s.clicked.connect(lambda: self.video_player.skip_seconds(5))
        btn_forward_5s.setEnabled(False)
        time_nav_layout.addWidget(btn_forward_5s)

        # Store refs for enabling/disabling
        self.nav_buttons = [btn_back_10f, btn_back_1f, btn_forward_1f, btn_forward_10f,
                           btn_back_5s, btn_back_1s, btn_forward_1s, btn_forward_5s]

        layout.addLayout(time_nav_layout)

        group.setLayout(layout)
        return group

    def _create_timeline_section(self):
        """Create timeline widget section"""
        group = QGroupBox("Timeline")
        layout = QVBoxLayout()

        self.timeline = TimelineWidget()
        self.timeline.frame_clicked.connect(self._on_timeline_clicked)
        layout.addWidget(self.timeline)

        # Timeline controls
        controls_layout = QHBoxLayout()
        zoom_in_btn = QPushButton("🔍+")
        zoom_in_btn.clicked.connect(self.timeline.zoom_in)
        zoom_out_btn = QPushButton("🔍-")
        zoom_out_btn.clicked.connect(self.timeline.zoom_out)

        controls_layout.addWidget(QLabel("Zoom:"))
        controls_layout.addWidget(zoom_in_btn)
        controls_layout.addWidget(zoom_out_btn)
        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        group.setLayout(layout)
        return group

    def _create_tracking_section(self):
        """Create tracking configuration section"""
        group = QGroupBox("2. Configuración de Tracking")
        layout = QVBoxLayout()

        # Tracker type
        tracker_layout = QHBoxLayout()
        tracker_layout.addWidget(QLabel("Tipo de tracker:"))
        self.tracker_combo = QComboBox()
        self.tracker_combo.addItems([
            "KCF - Rápido y estable (RECOMENDADO)",
            "CSRT - Muy preciso pero puede fallar",
            "MOSSE - Muy rápido",
            "MIL - Buen balance"
        ])
        tracker_layout.addWidget(self.tracker_combo)
        layout.addLayout(tracker_layout)

        # Both dancers visible
        self.both_visible_checkbox = QCheckBox("Ambos bailarines visibles desde el inicio")
        self.both_visible_checkbox.setChecked(True)
        self.both_visible_checkbox.stateChanged.connect(self._on_both_visible_changed)
        layout.addWidget(self.both_visible_checkbox)

        # Start time
        start_time_layout = QHBoxLayout()
        start_time_layout.addWidget(QLabel("Tiempo de inicio (segundos):"))
        self.start_time_spin = QSpinBox()
        self.start_time_spin.setMinimum(0)
        self.start_time_spin.setMaximum(10000)
        self.start_time_spin.setValue(0)
        self.start_time_spin.setEnabled(False)
        start_time_layout.addWidget(self.start_time_spin)
        layout.addLayout(start_time_layout)

        # Tracking buttons
        self.start_tracking_btn = QPushButton("🎯 Seleccionar Área")
        self.start_tracking_btn.clicked.connect(self._start_tracking)
        self.start_tracking_btn.setEnabled(False)
        self.start_tracking_btn.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
        layout.addWidget(self.start_tracking_btn)

        tracking_controls = QHBoxLayout()

        self.pause_tracking_btn = QPushButton("⏸ Pausar (Espacio)")
        self.pause_tracking_btn.clicked.connect(self._pause_tracking)
        self.pause_tracking_btn.setEnabled(False)
        tracking_controls.addWidget(self.pause_tracking_btn)

        self.reinit_btn = QPushButton("🔄 Re-seleccionar Área (R)")
        self.reinit_btn.clicked.connect(self._reinitialize_tracking)
        self.reinit_btn.setEnabled(False)
        tracking_controls.addWidget(self.reinit_btn)

        self.stop_tracking_btn = QPushButton("⏹ Detener (ESC)")
        self.stop_tracking_btn.clicked.connect(self._stop_tracking)
        self.stop_tracking_btn.setEnabled(False)
        tracking_controls.addWidget(self.stop_tracking_btn)

        layout.addLayout(tracking_controls)

        # Progress bar
        self.tracking_progress = QProgressBar()
        self.tracking_progress.setVisible(False)
        layout.addWidget(self.tracking_progress)

        group.setLayout(layout)
        return group

    def _create_export_section(self):
        """Create export configuration section"""
        group = QGroupBox("3. Configuración de Export")
        layout = QVBoxLayout()

        # Margin
        margin_layout = QVBoxLayout()
        margin_layout.addWidget(QLabel("Margen alrededor de bailarines:"))
        margin_slider_layout = QHBoxLayout()

        self.margin_slider = QSlider(Qt.Horizontal)
        self.margin_slider.setMinimum(10)
        self.margin_slider.setMaximum(25)
        self.margin_slider.setValue(15)
        self.margin_slider.setTickPosition(QSlider.TicksBelow)
        self.margin_slider.setTickInterval(5)
        self.margin_slider.valueChanged.connect(self._on_margin_changed)

        self.margin_label = QLabel("1.5x (Cómodo)")
        margin_slider_layout.addWidget(QLabel("Ajustado"))
        margin_slider_layout.addWidget(self.margin_slider, stretch=1)
        margin_slider_layout.addWidget(QLabel("Amplio"))
        margin_layout.addLayout(margin_slider_layout)
        margin_layout.addWidget(self.margin_label, alignment=Qt.AlignCenter)

        layout.addLayout(margin_layout)

        # Smooth
        smooth_layout = QVBoxLayout()
        smooth_layout.addWidget(QLabel("Suavizado de movimiento:"))
        smooth_slider_layout = QHBoxLayout()

        self.smooth_slider = QSlider(Qt.Horizontal)
        self.smooth_slider.setMinimum(5)
        self.smooth_slider.setMaximum(30)
        self.smooth_slider.setValue(10)
        self.smooth_slider.setTickPosition(QSlider.TicksBelow)
        self.smooth_slider.setTickInterval(5)
        self.smooth_slider.valueChanged.connect(self._on_smooth_changed)

        self.smooth_label = QLabel("10 frames (Normal)")
        smooth_slider_layout.addWidget(QLabel("Mínimo"))
        smooth_slider_layout.addWidget(self.smooth_slider, stretch=1)
        smooth_slider_layout.addWidget(QLabel("Suave"))
        smooth_layout.addLayout(smooth_slider_layout)
        smooth_layout.addWidget(self.smooth_label, alignment=Qt.AlignCenter)

        layout.addLayout(smooth_layout)

        # Output file
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Archivo de salida:"))
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setText(self._generate_output_filename())
        output_layout.addWidget(self.output_path_edit)

        browse_btn = QPushButton("...")
        browse_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(browse_btn)
        layout.addLayout(output_layout)

        # Export button
        self.export_btn = QPushButton("🎬 Exportar Video")
        self.export_btn.clicked.connect(self._start_export)
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
        layout.addWidget(self.export_btn)

        # Export progress
        self.export_progress = QProgressBar()
        self.export_progress.setVisible(False)
        layout.addWidget(self.export_progress)

        group.setLayout(layout)
        return group

    def _create_log_section(self):
        """Create log/status section"""
        group = QGroupBox("Estado y Mensajes")
        layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        layout.addWidget(self.log_text)

        group.setLayout(layout)
        return group

    def _apply_stylesheet(self):
        """Apply custom stylesheet"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                border: 2px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px 10px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QPushButton:disabled {
                background-color: #1a1a1a;
                color: #666666;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #3a3a3a;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 3px;
                color: #ffffff;
            }
            QTextEdit {
                background-color: #1a1a1a;
                border: 1px solid #555555;
                border-radius: 3px;
                color: #cccccc;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
                background-color: #1a1a1a;
            }
            QProgressBar::chunk {
                background-color: #4a90e2;
            }
            QSlider::groove:horizontal {
                border: 1px solid #555555;
                height: 8px;
                background: #1a1a1a;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4a90e2;
                border: 1px solid #555555;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)

    # Event handlers

    def _open_video(self):
        """Open video file dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Video",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv);;All Files (*.*)"
        )

        if file_path:
            self.video_path = file_path
            self.audio_path = file_path  # Use video audio by default

            # Load video
            if self.video_player.load_video(file_path):
                self.video_path_label.setText(os.path.basename(file_path))
                self._log(f"Video cargado: {file_path}")

                # Get video info
                info = self.video_player.get_video_info()
                if info:
                    info_text = f"{info['width']}x{info['height']} | {info['fps']:.1f} FPS | {info['duration']:.1f}s"
                    self.video_info_label.setText(info_text)

                    # Setup timeline
                    self.timeline.set_total_frames(info['total_frames'])

                # Enable controls
                self.play_pause_btn.setEnabled(True)
                for btn in self.nav_buttons:
                    btn.setEnabled(True)

                self.start_tracking_btn.setEnabled(True)

                # Check for existing coords
                self._check_existing_coords()
            else:
                QMessageBox.critical(self, "Error", "No se pudo abrir el video")

    def _open_audio(self):
        """Open audio file dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Audio",
            "",
            "Audio Files (*.mp3 *.wav *.aac *.m4a);;All Files (*.*)"
        )

        if file_path:
            self.audio_path = file_path
            self.audio_path_label.setText(f"Audio: {os.path.basename(file_path)}")
            self._log(f"Audio personalizado: {file_path}")

    def _check_existing_coords(self):
        """Check if coords.csv exists"""
        if os.path.exists(self.coords_csv):
            self.use_existing_checkbox.setEnabled(True)
            self._log("Coordenadas existentes encontradas (coords.csv)")
        else:
            self.use_existing_checkbox.setEnabled(False)
            self.use_existing_checkbox.setChecked(False)

    def _on_use_existing_changed(self, state):
        """Handle use existing coords checkbox"""
        if state == Qt.Checked:
            # Load existing coords and display on timeline
            self._load_existing_coords()
            self.export_btn.setEnabled(True)
        else:
            self.timeline.clear_states()

    def _load_existing_coords(self):
        """Load existing coordinates from CSV"""
        try:
            with open(self.coords_csv, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    frame = int(row['frame'])
                    self.timeline.set_frame_state(frame, TimelineWidget.STATE_TRACKED)

            self._log(f"Coordenadas cargadas desde {self.coords_csv}")
        except Exception as e:
            self._log(f"Error cargando coordenadas: {str(e)}")

    def _toggle_play_pause(self):
        """Toggle play/pause"""
        self.video_player.toggle_play_pause()
        if self.video_player.is_playing:
            self.play_pause_btn.setText("⏸ Pause")
        else:
            self.play_pause_btn.setText("▶ Play")

    def _on_speed_changed(self, text):
        """Handle playback speed change"""
        speed = float(text.replace('x', ''))
        self.video_player.set_playback_speed(speed)

    def _on_frame_changed(self, frame_number):
        """Handle frame change in video player"""
        self.timeline.set_current_frame(frame_number)

        # If tracking is active and paused, sync the thread's frame position
        if self.tracking_active and self.tracking_thread and self.tracking_thread.is_paused:
            self.tracking_thread.set_current_frame(frame_number)

            # Try to display bbox from coords if available
            if hasattr(self.tracking_thread, 'coords_dict') and frame_number in self.tracking_thread.coords_dict:
                _, x, y, w, h = self.tracking_thread.coords_dict[frame_number]
                self.video_player.set_bbox((x, y, w, h), 'green')
            else:
                # Keep last known bbox visible for reference
                # Don't clear it - user can see where the tracker was
                pass

    def _on_timeline_clicked(self, frame_number):
        """Handle timeline click"""
        self.video_player.seek_frame(frame_number)

    def _on_both_visible_changed(self, state):
        """Handle both dancers visible checkbox"""
        if state == Qt.Checked:
            self.start_time_spin.setEnabled(False)
            self.start_time_spin.setValue(0)
        else:
            self.start_time_spin.setEnabled(True)

    def _on_margin_changed(self, value):
        """Handle margin slider change"""
        margin = value / 10.0
        self.margin_label.setText(f"{margin:.1f}x ({'Ajustado' if margin < 1.3 else 'Cómodo' if margin < 1.8 else 'Amplio'})")

    def _on_smooth_changed(self, value):
        """Handle smooth slider change"""
        self.smooth_label.setText(f"{value} frames ({'Mínimo' if value < 10 else 'Normal' if value < 20 else 'Suave'})")

    def _browse_output(self):
        """Browse for output file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Video Como",
            self.output_path_edit.text(),
            "Video Files (*.mov *.mp4);;All Files (*.*)"
        )

        if file_path:
            self.output_path_edit.setText(file_path)

    def _generate_output_filename(self):
        """Generate default output filename with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"output_{timestamp}.mov"

    def _start_tracking(self):
        """Start tracking process"""
        if not self.video_path:
            QMessageBox.warning(self, "Error", "Por favor carga un video primero")
            return

        # Get tracker type
        tracker_text = self.tracker_combo.currentText()
        tracker_type = tracker_text.split(' ')[0]  # Get first word (KCF, CSRT, etc.)

        # Get start frame
        start_time = self.start_time_spin.value()
        info = self.video_player.get_video_info()
        start_frame = int(start_time * info['fps']) if info else 0

        # Seek to start frame
        self.video_player.seek_frame(start_frame)

        # Pause playback
        self.video_player.pause()

        # Create tracking thread
        self.tracking_thread = TrackingThread(self.video_path, tracker_type, start_frame)
        self.tracking_thread.progress_update.connect(self._on_tracking_progress)
        self.tracking_thread.frame_tracked.connect(self._on_frame_tracked)
        self.tracking_thread.tracking_complete.connect(self._on_tracking_complete)
        self.tracking_thread.tracking_error.connect(self._on_tracking_error)
        self.tracking_thread.request_bbox.connect(self._on_bbox_requested)

        # Enable selection mode
        self.video_player.start_selection()
        self._log("Dibuja un rectángulo alrededor de los bailarines. Luego presiona Espacio o Reanudar para iniciar.")

        # Update UI
        self.tracking_active = True
        self.start_tracking_btn.setEnabled(False)
        self.pause_tracking_btn.setEnabled(True)
        self.reinit_btn.setEnabled(True)
        self.stop_tracking_btn.setEnabled(True)
        self.tracking_progress.setVisible(True)

    def _on_bbox_requested(self, frame_number):
        """Handle bbox selection request from tracking thread"""
        self.video_player.seek_frame(frame_number)
        self.video_player.start_selection()
        self._log(f"Selecciona el área para el frame {frame_number}")

    def _on_bbox_selected(self, bbox):
        """Handle bbox selection from video player"""
        if self.tracking_thread:
            if self.tracking_thread.initial_bbox is None:
                # First bbox selection - start thread (will be in paused state)
                self.tracking_thread.set_initial_bbox(bbox)
                self.tracking_thread.start()  # Thread starts but is paused by default
                self._log("Área seleccionada. Presiona Reanudar o Espacio para iniciar el tracking.")
                # Update button state to show paused
                self.pause_tracking_btn.setText("▶ Reanudar")
            else:
                # Reinitialize bbox - stays paused
                self.tracking_thread.set_reinitialize_bbox(bbox)
                self._log("Área re-seleccionada. Presiona Reanudar o Espacio para continuar.")

    def _pause_tracking(self):
        """Pause/resume tracking"""
        if self.tracking_thread:
            if self.tracking_thread.is_paused:
                # Resuming - sync frame position
                current_video_frame = self.video_player.current_frame
                self.tracking_thread.set_current_frame(current_video_frame)

                # Only reinitialize if user navigated to a different frame
                # (not on first resume right after bbox selection)
                if self.last_resume_frame is not None and self.last_resume_frame != current_video_frame:
                    # User navigated - tell thread to reinitialize when it resumes
                    self.tracking_thread.needs_reinitialization = True
                    self._log(f"Reanudando desde frame {current_video_frame} (reinicializando tracker)")
                else:
                    self.tracking_thread.needs_reinitialization = False
                    self._log(f"Tracking reanudado desde frame {current_video_frame}")

                self.last_resume_frame = current_video_frame
                self.tracking_thread.resume()
                self.pause_tracking_btn.setText("⏸ Pausar (Espacio)")
            else:
                self.tracking_thread.pause()
                self.pause_tracking_btn.setText("▶ Reanudar")
                self._log("Tracking pausado. Puedes navegar libremente con las flechas o botones.")

    def _reinitialize_tracking(self):
        """Request tracker reinitialization"""
        if self.tracking_thread:
            self.tracking_thread.request_reinitialize()
            # Enable selection mode to allow user to draw new bbox
            self.video_player.start_selection()
            # Update button to show paused state
            self.pause_tracking_btn.setText("▶ Reanudar")
            self._log("Selecciona el área alrededor de los bailarines... (Presiona Reanudar o Espacio cuando estés listo)")

    def _stop_tracking(self):
        """Stop tracking process"""
        if self.tracking_thread:
            self.tracking_thread.stop()
            self.tracking_thread.wait()
            self._log("Tracking detenido por el usuario")

            # Save what we have
            if self.tracking_thread.coords_dict:
                self._save_coords_to_csv(self.tracking_thread.coords_dict)

            self._reset_tracking_ui()

    def _on_tracking_progress(self, frame, total, status):
        """Handle tracking progress update"""
        progress = int((frame / total) * 100)
        self.tracking_progress.setValue(progress)
        self._log(f"Frame {frame}/{total}: {status}", replace_last=True)

    def _on_frame_tracked(self, frame_number, bbox, color):
        """Handle frame tracked signal"""
        # Update timeline
        if color == 'green':
            state = TimelineWidget.STATE_TRACKED
        elif color == 'orange':
            state = TimelineWidget.STATE_PROBLEM
        elif color == 'red':
            state = TimelineWidget.STATE_PROBLEM
        else:
            state = TimelineWidget.STATE_TRACKED

        self.timeline.set_frame_state(frame_number, state)

        # Only seek if frame is different from current (prevents redundant seek and file contention)
        if frame_number != self.video_player.current_frame:
            self.video_player.seek_frame(frame_number)

        # Update video player display with bbox (set_bbox now redraws without seeking)
        if bbox:
            self.video_player.set_bbox(bbox, color)
        else:
            # No bbox means tracking lost - show red indicator
            self.video_player.clear_bbox()
            # Update button to show paused state
            self.pause_tracking_btn.setText("▶ Reanudar")

    def _on_tracking_complete(self, coords_dict):
        """Handle tracking completion"""
        self._log("Tracking completado!")

        # Save to CSV
        self._save_coords_to_csv(coords_dict)

        # Enable export
        self.export_btn.setEnabled(True)

        self._reset_tracking_ui()

    def _on_tracking_error(self, error_msg):
        """Handle tracking error"""
        self._log(f"Error en tracking: {error_msg}")
        QMessageBox.critical(self, "Error de Tracking", error_msg)
        self._reset_tracking_ui()

    def _reset_tracking_ui(self):
        """Reset tracking UI to initial state"""
        self.tracking_active = False
        self.last_resume_frame = None  # Reset resume tracking
        self.start_tracking_btn.setEnabled(True)
        self.pause_tracking_btn.setEnabled(False)
        self.reinit_btn.setEnabled(False)
        self.stop_tracking_btn.setEnabled(False)
        self.tracking_progress.setVisible(False)
        self.tracking_progress.setValue(0)

    def _save_coords_to_csv(self, coords_dict):
        """Save coordinates to CSV file"""
        try:
            sorted_frames = sorted(coords_dict.keys())
            with open(self.coords_csv, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['frame', 'x', 'y', 'w', 'h'])

                for frame_num in sorted_frames:
                    frame, x, y, w, h = coords_dict[frame_num]
                    writer.writerow([frame, x, y, w, h])

            self._log(f"Coordenadas guardadas en {self.coords_csv}")
        except Exception as e:
            self._log(f"Error guardando coordenadas: {str(e)}")

    def _start_export(self):
        """Start export process"""
        if not self.video_path:
            QMessageBox.warning(self, "Error", "No hay video cargado")
            return

        if not os.path.exists(self.coords_csv):
            QMessageBox.warning(self, "Error", "No hay coordenadas de tracking disponibles")
            return

        # Get export parameters
        margin = self.margin_slider.value() / 10.0
        smooth = self.smooth_slider.value()
        output_path = self.output_path_edit.text()

        # Use custom audio if specified, otherwise use video audio
        audio_source = self.audio_path if self.audio_path else self.video_path

        # Create export thread
        self.export_thread = ExportThread(
            self.video_path,
            self.coords_csv,
            output_path,
            margin,
            smooth
        )
        self.export_thread.progress_update.connect(self._on_export_progress)
        self.export_thread.export_complete.connect(self._on_export_complete)
        self.export_thread.export_error.connect(self._on_export_error)

        # Update UI
        self.export_btn.setEnabled(False)
        self.export_progress.setVisible(True)
        self._log("Exportando video...")

        # Start export
        self.export_thread.start()

    def _on_export_progress(self, current, total, status):
        """Handle export progress update"""
        self.export_progress.setValue(current)
        self._log(status, replace_last=True)

    def _on_export_complete(self, output_path):
        """Handle export completion"""
        self._log(f"¡Exportación completa! Archivo: {output_path}")
        self.export_progress.setVisible(False)
        self.export_btn.setEnabled(True)

        # Show completion dialog
        result = QMessageBox.information(
            self,
            "Exportación Completa",
            f"Video exportado exitosamente:\n{output_path}\n\n¿Deseas abrir la carpeta?",
            QMessageBox.Yes | QMessageBox.No
        )

        if result == QMessageBox.Yes:
            import subprocess
            folder = os.path.dirname(output_path)
            if os.name == 'nt':  # Windows
                subprocess.Popen(['explorer', folder])
            else:  # macOS/Linux
                subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', folder])

    def _on_export_error(self, error_msg):
        """Handle export error"""
        self._log(f"Error en export: {error_msg}")
        QMessageBox.critical(self, "Error de Export", error_msg)
        self.export_progress.setVisible(False)
        self.export_btn.setEnabled(True)

    def _log(self, message, replace_last=False):
        """Add message to log"""
        if replace_last:
            # Get all text, remove last line, add new message
            text = self.log_text.toPlainText()
            lines = text.split('\n')
            if lines:
                lines[-1] = message
                self.log_text.setPlainText('\n'.join(lines))
            else:
                self.log_text.append(message)
        else:
            self.log_text.append(message)

        # Auto-scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key_Space:
            # If tracking is active, pause/resume tracking
            # Otherwise, toggle video playback
            if self.tracking_active:
                self._pause_tracking()
            else:
                self._toggle_play_pause()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # Enter/Return also pauses/resumes tracking when active
            if self.tracking_active:
                self._pause_tracking()
        elif event.key() == Qt.Key_R and self.tracking_active:
            self._reinitialize_tracking()
        elif event.key() == Qt.Key_Escape and self.tracking_active:
            self._stop_tracking()
        elif event.key() == Qt.Key_Left:
            self.video_player.prev_frame()
        elif event.key() == Qt.Key_Right:
            self.video_player.next_frame()
        elif event.key() == Qt.Key_A:
            # A = -10 frames (matching original track_improved.py)
            self.video_player.seek_frame(self.video_player.current_frame - 10)
        elif event.key() == Qt.Key_D:
            # D = +10 frames (matching original track_improved.py)
            self.video_player.seek_frame(self.video_player.current_frame + 10)
        elif event.key() == Qt.Key_W:
            # W = -5 seconds (matching original track_improved.py)
            self.video_player.skip_seconds(-5)
        elif event.key() == Qt.Key_S:
            # S = +5 seconds (matching original track_improved.py)
            self.video_player.skip_seconds(5)
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Handle window close"""
        # Stop any running threads
        if self.tracking_thread and self.tracking_thread.isRunning():
            self.tracking_thread.stop()
            self.tracking_thread.wait()

        if self.export_thread and self.export_thread.isRunning():
            self.export_thread.stop()
            self.export_thread.wait()

        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Dancer Tracking")

    window = DancerTrackingUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
