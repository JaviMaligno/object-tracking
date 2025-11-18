# YOLO Tracking para Bailarines

Implementación de tracking de bailarines usando YOLOv8 + BoT-SORT, diseñado para manejar mejor los cambios de escala, alejamiento y acercamiento.

## 📋 Características

### Ventajas sobre OpenCV CSRT

| Característica | OpenCV CSRT | YOLOv8 + BoT-SORT |
|----------------|-------------|-------------------|
| **Cambios de escala** | ⭐⭐⭐ Limitado | ⭐⭐⭐⭐⭐ Excelente |
| **Alejamiento/acercamiento** | ⭐⭐ Regular | ⭐⭐⭐⭐⭐ Excelente |
| **Re-inicialización** | ⚠️ Manual (tecla R) | ✅ Automática |
| **Multi-objeto** | ⚠️ No | ✅ Sí (IDs por bailarín) |
| **Velocidad CPU** | ⭐⭐⭐⭐⭐ ~30 FPS | ⭐⭐ ~5-8 FPS |
| **Oclusiones** | ⭐⭐ Regular | ⭐⭐⭐⭐ Muy bueno |
| **Precisión** | ⭐⭐⭐ Buena | ⭐⭐⭐⭐⭐ Excelente |

### ¿Por qué YOLO maneja mejor la escala?

**OpenCV CSRT:**
- Trackea **features** del frame inicial
- Si el objeto cambia de tamaño, puede perder features
- Requiere re-inicialización manual cuando falla

**YOLOv8:**
- **Re-detecta** personas en cada frame
- El detector es **scale-invariant** (entrenado en múltiples escalas)
- Detección automática sin importar tamaño
- Tracking solo asocia detecciones entre frames

## 🚀 Instalación

```bash
# Activar entorno virtual
source venv/Scripts/activate  # Windows Git Bash
# o
venv\Scripts\activate  # Windows CMD

# Instalar dependencias (ya instaladas en este proyecto)
pip install ultralytics>=8.3.0
```

## 📦 Archivos Creados

1. **`test_yolo_tracking.py`** - Proof of concept y tests
2. **`track_yolo.py`** - Clase principal `YOLODancerTracker`
3. **`tracking_thread_yolo.py`** - Thread para integración con UI
4. **`README_YOLO.md`** - Esta documentación

## 🎯 Uso

### Opción 1: Script Standalone (Sin UI)

```bash
# Tracking básico
python track_yolo.py video.mp4

# Especificar archivo de salida
python track_yolo.py video.mp4 coords_yolo.csv
```

#### Salidas generadas:
- `coords_yolo.csv` - Coordenadas individuales por bailarín (con track_id)
- `coords_yolo_combined.csv` - Coordenadas combinadas (compatible con `export_final.py`)

### Opción 2: Proof of Concept

```bash
# Test sin video (solo carga modelo)
python test_yolo_tracking.py

# Test con video (procesa primeros 10 frames)
python test_yolo_tracking.py video.mp4
```

### Opción 3: Integración con UI (Próximamente)

La integración con la UI existente está lista mediante `tracking_thread_yolo.py`, pero requiere actualizar `dancer_tracking_ui.py` para incluir un selector de backend (OpenCV vs YOLO).

## 💻 Uso Programático

```python
from track_yolo import YOLODancerTracker

# Crear tracker
tracker = YOLODancerTracker(
    video_path="video.mp4",
    model_size="n",  # n=nano (6MB, rápido en CPU)
    tracker_type="botsort",  # botsort o bytetrack
    conf_threshold=0.3
)

# Ejecutar tracking
coords = tracker.track_video()

# Guardar resultados
tracker.save_coords_csv("output.csv", mode="individual")  # Por bailarín
tracker.save_coords_csv("output_combined.csv", mode="combined")  # Combinado

# Visualizar (opcional)
tracker.visualize_tracking(output_video="tracked.mp4", max_frames=100)
```

## 📊 Comparación de Modelos YOLO

| Modelo | Tamaño | Velocidad CPU | Precisión | Recomendado para |
|--------|--------|---------------|-----------|------------------|
| **yolov8n** | 6.3 MB | ~5-8 FPS | ⭐⭐⭐⭐ | CPU (recomendado) |
| yolov8s | 22 MB | ~2-4 FPS | ⭐⭐⭐⭐⭐ | GPU |
| yolov8m | 52 MB | ~1-2 FPS | ⭐⭐⭐⭐⭐ | GPU |
| yolov8l | 87 MB | <1 FPS | ⭐⭐⭐⭐⭐ | GPU |

**Nota:** Las velocidades son aproximadas en CPU moderno. Con GPU son 10-20x más rápidas.

## 🔧 Configuración Avanzada

### Cambiar modelo YOLO

```python
# Usar modelo más grande (requiere más tiempo pero mejor precisión)
tracker = YOLODancerTracker(
    video_path="video.mp4",
    model_size="s",  # small en lugar de nano
    ...
)
```

### Cambiar tracker

```python
# ByteTrack es más rápido pero menos preciso que BoT-SORT
tracker = YOLODancerTracker(
    video_path="video.mp4",
    tracker_type="bytetrack",  # en lugar de botsort
    ...
)
```

### Ajustar umbral de confianza

```python
# Más alto = menos falsos positivos, pero puede perder detecciones
# Más bajo = más detecciones, pero más falsos positivos
tracker = YOLODancerTracker(
    video_path="video.mp4",
    conf_threshold=0.5,  # default 0.3
    ...
)
```

## 📈 Formato de Salida

### CSV Individual (`coords_yolo.csv`)

```csv
frame,track_id,x,y,w,h,conf
0,0,100,200,150,300,0.95
0,1,400,200,150,300,0.92
1,0,105,205,150,300,0.94
1,1,405,205,150,300,0.93
...
```

### CSV Combinado (`coords_yolo_combined.csv`)

Compatible con `export_final.py`:

```csv
frame,x,y,w,h
0,100,200,450,300
1,105,205,450,300
...
```

## 🔄 Exportar Video Final

Una vez que tienes el archivo CSV combinado:

```bash
# Usar el export existente (100% compatible)
python export_final.py coords_yolo_combined.csv
```

## 🐛 Troubleshooting

### Error: "Cannot open video file"

```bash
# Verificar que el archivo existe y tiene una ruta válida
python check_video.py video.mp4
```

### Tracking muy lento en CPU

```bash
# Opciones para mejorar velocidad:
# 1. Usar modelo más pequeño (ya usando yolov8n)
# 2. Reducir resolución del video antes de procesar
# 3. Procesar en GPU si está disponible
```

### "No detections" en muchos frames

```bash
# Reducir umbral de confianza
python track_yolo.py video.mp4 --conf 0.2  # default 0.3
```

## 📚 Benchmarks

### DanceTrack Dataset (específico para baile)

| Tracker | HOTA | Notas |
|---------|------|-------|
| **OC-SORT** | 54.2% | Mejor para movimiento no-lineal |
| **BoT-SORT** | 53.8% | Mejor con cámara móvil |
| ByteTrack | 47.3% | Más rápido |
| DeepSORT | 45.6% | Basado en apariencia |

**Nota:** DanceTrack es muy difícil por ropa similar y movimientos complejos.

## 🔗 Referencias

- **YOLOv8 Docs:** https://docs.ultralytics.com/
- **Tracking Mode:** https://docs.ultralytics.com/modes/track/
- **DanceTrack:** https://dancetrack.github.io/
- **BoT-SORT Paper:** https://github.com/NirAharon/BoT-SORT

## 🤝 Integración Futura

### Próximos pasos para UI:

1. Añadir dropdown en `dancer_tracking_ui.py` para seleccionar backend:
   - OpenCV CSRT (actual)
   - YOLOv8 + BoT-SORT (nuevo)

2. Usar `tracking_thread_yolo.py` cuando se seleccione YOLO

3. Mantener compatibilidad con export actual (ya implementado via CSV combinado)

### Ejemplo de selector de backend:

```python
# En dancer_tracking_ui.py
self.backend_combo = QComboBox()
self.backend_combo.addItems(["OpenCV CSRT", "YOLOv8 + BoT-SORT"])

# Al iniciar tracking:
if self.backend_combo.currentText() == "YOLOv8 + BoT-SORT":
    self.tracking_thread = TrackingThreadYOLO(...)
else:
    self.tracking_thread = TrackingThread(...)
```

## 📝 Notas Importantes

### CPU vs GPU

- **CPU:** Usar yolov8n (nano), ~5-8 FPS, suficiente para procesamiento offline
- **GPU:** Usar yolov8s o mayor, ~20-60 FPS, ideal para tiempo real

### Comparación con OpenCV

**Cuándo usar YOLO:**
- ✅ Bailarines se acercan/alejan significativamente
- ✅ Cambios de escala frecuentes
- ✅ Movimientos rápidos o complejos
- ✅ Procesamiento offline (no requiere tiempo real)
- ✅ Quieres tracking automático sin intervención

**Cuándo usar OpenCV CSRT:**
- ✅ Bailarines mantienen tamaño relativamente constante
- ✅ Necesitas máxima velocidad en CPU
- ✅ Video corto o pocos cambios de escala
- ✅ Procesamiento en hardware antiguo

## 🎉 Resultados Esperados

Con YOLOv8 + BoT-SORT deberías ver:

1. **Sin pérdida de tracking** durante cambios de escala
2. **Detección automática** sin tecla 'R'
3. **IDs persistentes** por cada bailarín
4. **Mejor manejo** de oclusiones y cruces
5. **Tracking más robusto** en general

---

**Desarrollado para:** Dancer Tracking Project
**Fecha:** Noviembre 2024
**Versión YOLO:** 8.3.228
**Licencia:** Compatible con proyecto principal
