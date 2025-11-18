# 🎬 Dancer Tracking & Auto-Crop

Sistema completo para seguir y recortar automáticamente bailarines en videos usando YOLOv8, **sin GPU** obligatoria (aunque recomendada) y preservando la calidad original.

## 📂 Nueva Estructura del Proyecto

```
dancer_tracking/
├── data/                  # Videos de entrada, audio y modelos (yolov8n.pt)
├── outputs/               # Resultados: CSVs, videos exportados, gráficos
├── docs/                  # Documentación y guías detalladas
├── scripts/               # Scripts de utilidad y análisis
├── ui/                    # Interfaz gráfica experimental (beta)
├── tests/                 # Tests unitarios
├── models/                # Modelos de YOLO descargados
├── track_yolo.py          # Script principal de tracking (YOLO + BoT-SORT)
├── export_final.py        # Script principal de exportación (Crop + FFmpeg)
├── requirements.txt       # Dependencias Python
└── README.md              # Este archivo
```

---

## 🚀 Inicio Rápido

### 1. Instalación

**Requisito:** Python 3.8+

```bash
pip install -r requirements.txt
```

(Opcional) Instala FFmpeg si no lo tienes (el script intentará usarlo si está en el sistema o en `ffmpeg/bin`).

### 2. Tracking (Generar Coordenadas)

Usa `track_yolo.py` para analizar el video y generar el archivo de coordenadas.

```bash
# Uso básico (busca video en data/ y guarda en outputs/)
python track_yolo.py data/tu_video.mov

# Uso explícito
python track_yolo.py data/tu_video.mov outputs/mis_coords.csv
```

Esto generará dos archivos en `outputs/`:
1. `coords_yolo.csv`: Coordenadas individuales por bailarín (ID, x, y, w, h).
2. `coords_yolo_combined.csv`: Coordenadas combinadas (bounding box total) listas para el export.

### 3. Exportación (Crear Video Recortado)

Usa `export_final.py` para generar el video final recortado.

```bash
# Uso básico (usa configuración por defecto)
python export_final.py data/tu_video.mov outputs/coords_yolo_combined.csv outputs/video_final.mov

# Uso recomendado para Instagram (4:5 vertical, crop adaptativo)
python export_final.py data/tu_video.mov outputs/coords_yolo_combined.csv outputs/instagram.mov --aspect-ratio instagram --adaptive-crop
```

---

## ⚙️ Parámetros Principales

### `export_final.py`

| Opción | Descripción | Ejemplo |
|--------|-------------|---------|
| `--aspect-ratio` | Ratio de aspecto deseado (`instagram`, `9:16`, `1:1`, `16:9`, `auto`) | `--aspect-ratio instagram` |
| `--adaptive-crop` | Ajusta el zoom dinámicamente para no cortar a los bailarines (Recomendado) | `--adaptive-crop` |
| `--margin` | Factor de margen alrededor de los bailarines (Default: 1.5) | `--margin 1.8` |
| `--smooth` | Ventana de suavizado para evitar movimientos bruscos (Default: 15) | `--smooth 20` |

---

## 🖥️ Interfaz Gráfica (Experimental)

La interfaz gráfica se encuentra en la carpeta `ui/`. Es un experimento para facilitar el uso, pero los scripts de consola son más robustos actualmente.

Para probarla:
```bash
cd ui
start_ui.bat
```

---

## 📝 Notas

- **Modelos YOLO:** La primera vez que ejecutes el tracking, se descargará automáticamente el modelo `yolov8n.pt` en la carpeta `models/`.
- **FFmpeg:** Se requiere FFmpeg para la exportación de alta calidad. El script buscará `ffmpeg` en el PATH del sistema o en la carpeta local `ffmpeg/`.

## 🆘 Soporte

Si encuentras problemas, revisa la carpeta `docs/` para guías más detalladas sobre calidad y solución de problemas.
