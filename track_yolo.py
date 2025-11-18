"""
track_yolo.py - Tracking de bailarines con YOLOv8 + BoT-SORT
Compatible con la arquitectura existente del proyecto
Genera coords.csv compatible con export_final.py
"""

import sys
import cv2
import csv
import numpy as np
from ultralytics import YOLO
from pathlib import Path
from tqdm import tqdm


class YOLODancerTracker:
    """
    Tracker de bailarines usando YOLOv8 + BoT-SORT

    Ventajas sobre OpenCV trackers:
    - Re-detección automática (no requiere tecla 'R')
    - Manejo excelente de cambios de escala
    - Multi-object tracking nativo (cada bailarín con su ID)
    - Tracking robusto con oclusiones
    """

    def __init__(self, video_path, model_size="n", tracker_type="botsort", conf_threshold=0.3):
        """
        Inicializa el tracker YOLO

        Args:
            video_path: Ruta al archivo de video
            model_size: Tamaño del modelo YOLO (n, s, m, l, x)
                       'n' = nano (6MB, recomendado para CPU)
                       's' = small (22MB)
            tracker_type: Tipo de tracker ('botsort' o 'bytetrack')
            conf_threshold: Umbral de confianza para detecciones (0.0-1.0)
        """
        self.video_path = video_path
        self.model_size = model_size
        self.tracker_type = tracker_type
        self.conf_threshold = conf_threshold

        # Cargar modelo YOLO
        model_name = f"yolov8{model_size}.pt"
        model_path = Path(f"models/{model_name}")
        
        if model_path.exists():
            print(f"Cargando modelo desde {model_path}...")
            self.model = YOLO(str(model_path))
        else:
            print(f"Cargando modelo {model_name} (se descargará si no existe)...")
            self.model = YOLO(model_name)

        # Información del video
        self.cap = cv2.VideoCapture(video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.cap.release()

        # Almacenamiento de coordenadas por frame
        self.coords_dict = {}  # {frame_num: {track_id: (x, y, w, h, conf)}}

        print(f"Video: {self.width}x{self.height} @ {self.fps} FPS")
        print(f"Total frames: {self.frame_count}")
        print(f"Duración: {self.frame_count/self.fps:.1f}s")
        print(f"Tracker: {tracker_type.upper()}")
        print(f"Umbral de confianza: {conf_threshold}")

    def track_video(self, progress_callback=None):
        """
        Ejecuta el tracking en todo el video

        Args:
            progress_callback: Función callback(frame_num, total_frames) para progreso

        Returns:
            dict: Diccionario con coordenadas por frame
        """
        print("\nIniciando tracking...")

        # Ejecutar tracking con YOLO
        results = self.model.track(
            source=self.video_path,
            tracker=f"{self.tracker_type}.yaml",
            device="cpu",
            classes=[0],  # Solo personas
            persist=True,  # Mantener IDs entre frames
            conf=self.conf_threshold,
            verbose=False,
            stream=True  # Streaming para procesar frame por frame
        )

        frame_num = 0

        for result in tqdm(results, total=self.frame_count, desc="Tracking"):
            boxes = result.boxes

            if boxes is not None and len(boxes) > 0:
                frame_detections = {}

                for box in boxes:
                    # Extraer información
                    track_id = int(box.id[0]) if box.id is not None else -1
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0])

                    # Convertir a formato (x, y, w, h)
                    x, y = int(x1), int(y1)
                    w, h = int(x2 - x1), int(y2 - y1)

                    frame_detections[track_id] = (x, y, w, h, conf)

                # Guardar detecciones del frame
                if len(frame_detections) > 0:
                    self.coords_dict[frame_num] = frame_detections

            # Callback de progreso
            if progress_callback is not None:
                progress_callback(frame_num, self.frame_count)

            frame_num += 1

        print(f"\nTracking completado: {frame_num} frames procesados")

        # Estadísticas
        self._print_statistics()

        return self.coords_dict

    def _print_statistics(self):
        """Imprime estadísticas del tracking"""
        total_frames_with_detections = len(self.coords_dict)
        total_detections = sum(len(dets) for dets in self.coords_dict.values())

        # Contar IDs únicos
        all_ids = set()
        for frame_dets in self.coords_dict.values():
            for track_id in frame_dets.keys():
                if track_id != -1:
                    all_ids.add(track_id)

        # Conteo por ID
        id_frame_count = {}
        for track_id in all_ids:
            id_frame_count[track_id] = sum(
                1 for dets in self.coords_dict.values() if track_id in dets
            )

        print("\nEstadísticas del tracking:")
        print(f"  - Frames con detecciones: {total_frames_with_detections}/{self.frame_count}")
        print(f"  - Total de detecciones: {total_detections}")
        print(f"  - Promedio detecciones/frame: {total_detections/max(1, total_frames_with_detections):.2f}")
        print(f"  - IDs únicos detectados: {len(all_ids)}")

        if len(all_ids) > 0:
            print(f"  - IDs: {sorted(all_ids)}")
            print("\n  Frames por ID:")
            for track_id in sorted(all_ids):
                frames = id_frame_count[track_id]
                percentage = (frames / self.frame_count) * 100
                print(f"    ID {track_id}: {frames} frames ({percentage:.1f}%)")

    def save_coords_csv(self, output_csv="coords_yolo.csv", mode="individual"):
        """
        Guarda las coordenadas en formato CSV

        Args:
            output_csv: Ruta del archivo CSV de salida
            mode: Modo de guardado:
                  'individual' - Cada bailarín en su propia fila (con track_id)
                  'combined' - Bounding box que engloba a ambos bailarines (compatible con export actual)
        """
        if mode == "individual":
            self._save_individual_csv(output_csv)
        elif mode == "combined":
            self._save_combined_csv(output_csv)
        else:
            raise ValueError(f"Modo no válido: {mode}. Usa 'individual' o 'combined'")

    def _save_individual_csv(self, output_csv):
        """Guarda CSV con cada bailarín en su propia fila"""
        print(f"\nGuardando coordenadas individuales en {output_csv}...")

        with open(output_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['frame', 'track_id', 'x', 'y', 'w', 'h', 'conf'])

            for frame_num in sorted(self.coords_dict.keys()):
                detections = self.coords_dict[frame_num]
                for track_id, (x, y, w, h, conf) in detections.items():
                    writer.writerow([frame_num, track_id, x, y, w, h, f"{conf:.3f}"])

        print(f"✓ Archivo guardado: {output_csv}")

    def _save_combined_csv(self, output_csv):
        """Guarda CSV con bbox que engloba a ambos bailarines (compatible con export_final.py)"""
        print(f"\nGuardando coordenadas combinadas en {output_csv}...")

        with open(output_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['frame', 'x', 'y', 'w', 'h'])

            for frame_num in sorted(self.coords_dict.keys()):
                detections = self.coords_dict[frame_num]

                if len(detections) > 0:
                    # Encontrar bbox que engloba todos los bailarines
                    all_boxes = []
                    for track_id, (x, y, w, h, conf) in detections.items():
                        all_boxes.append([x, y, x+w, y+h])

                    all_boxes = np.array(all_boxes)
                    x_min = int(all_boxes[:, 0].min())
                    y_min = int(all_boxes[:, 1].min())
                    x_max = int(all_boxes[:, 2].max())
                    y_max = int(all_boxes[:, 3].max())

                    w = x_max - x_min
                    h = y_max - y_min

                    writer.writerow([frame_num, x_min, y_min, w, h])

        print(f"✓ Archivo guardado: {output_csv}")

    def visualize_tracking(self, output_video=None, max_frames=None):
        """
        Crea un video con visualización del tracking

        Args:
            output_video: Ruta del video de salida (None = mostrar en pantalla)
            max_frames: Número máximo de frames a procesar (None = todos)
        """
        print("\nCreando visualización del tracking...")

        cap = cv2.VideoCapture(self.video_path)

        # Configurar writer si se guarda video
        writer = None
        if output_video:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(output_video, fourcc, self.fps, (self.width, self.height))

        # Colores para diferentes IDs
        colors = {
            0: (0, 255, 0),    # Verde
            1: (255, 0, 0),    # Azul
            2: (0, 0, 255),    # Rojo
            3: (255, 255, 0),  # Cyan
            4: (255, 0, 255),  # Magenta
            5: (0, 255, 255),  # Amarillo
        }

        frame_num = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if max_frames and frame_num >= max_frames:
                break

            # Dibujar detecciones si existen
            if frame_num in self.coords_dict:
                detections = self.coords_dict[frame_num]

                for track_id, (x, y, w, h, conf) in detections.items():
                    # Color según ID
                    color = colors.get(track_id, (255, 255, 255))

                    # Dibujar bbox
                    cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

                    # Label con ID y confianza
                    label = f"ID:{track_id} ({conf:.2f})"
                    cv2.putText(frame, label, (x, y-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # Info del frame
            info_text = f"Frame: {frame_num}/{self.frame_count}"
            cv2.putText(frame, info_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # Guardar o mostrar
            if writer:
                writer.write(frame)
            else:
                cv2.imshow("YOLO Tracking", frame)
                if cv2.waitKey(1) & 0xFF == 27:  # ESC para salir
                    break

            frame_num += 1

            if frame_num % 100 == 0:
                print(f"Visualizando: {frame_num}/{self.frame_count} frames")

        cap.release()
        if writer:
            writer.release()
            print(f"✓ Video guardado: {output_video}")
        else:
            cv2.destroyAllWindows()


def main():
    """Ejemplo de uso"""
    import sys

    if len(sys.argv) < 2:
        print("Uso: python track_yolo.py <video_path> [output_csv]")
        print("\nEjemplo:")
        print("  python track_yolo.py data/IMG_3048_con_Arjona.mov")
        print("  python track_yolo.py data/IMG_3048_con_Arjona.mov outputs/coords_yolo.csv")
        return 1

    video_path = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) > 2 else "outputs/coords_yolo.csv"

    # Verificar que el video existe
    if not Path(video_path).exists():
        print(f"Error: No se encuentra el archivo de video: {video_path}")
        return 1

    try:
        # Crear tracker
        tracker = YOLODancerTracker(
            video_path=video_path,
            model_size="n",  # nano (más rápido en CPU)
            tracker_type="botsort",  # botsort o bytetrack
            conf_threshold=0.3
        )

        # Ejecutar tracking
        coords = tracker.track_video()

        # Guardar en ambos formatos
        print("\n" + "="*60)
        print("Guardando resultados...")
        print("="*60)

        # Formato individual (con track_id por bailarín)
        tracker.save_coords_csv(output_csv, mode="individual")

        # Formato combinado (compatible con export_final.py actual)
        combined_csv = output_csv.replace('.csv', '_combined.csv')
        tracker.save_coords_csv(combined_csv, mode="combined")

        print("\n" + "="*60)
        print("TRACKING COMPLETADO")
        print("="*60)
        print(f"\nArchivos generados:")
        print(f"  1. {output_csv} - Coordenadas individuales por bailarín")
        print(f"  2. {combined_csv} - Coordenadas combinadas (compatible con export actual)")

        print("\nPara exportar el video con los crops:")
        print(f"  python export_final.py {combined_csv}")

        return 0

    except Exception as e:
        print(f"\nError durante el tracking: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
