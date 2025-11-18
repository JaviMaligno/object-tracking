# Guía de Exportación para Instagram

## 🎯 Resumen

Ahora puedes exportar videos de tracking directamente en formato Instagram (4:5) y otros formatos populares, con **zoom adaptativo** que previene que se corten los bailarines cuando están cerca de la cámara.

## 📱 Formato Instagram

**Especificaciones:**
- Aspect ratio: **4:5** (vertical portrait)
- Resolución: **1080 x 1350 px**
- Optimizado para máximo engagement en Instagram feed
- **NUEVO**: Zoom adaptativo para evitar cortes

## ✨ Zoom Adaptativo (NUEVO)

**Problema resuelto:** Cuando los bailarines están cerca de la cámara, el crop fijo de Instagram los cortaba por arriba/abajo.

**Solución:** El zoom adaptativo ajusta automáticamente el tamaño del crop frame por frame, manteniéndose en 4:5 pero "alejándose" cuando los bailarines están muy cerca, y luego volviendo al zoom normal. El resultado final siempre es 1080x1350px perfecto para Instagram.

**Activación:**
- **UI**: Checkbox "Zoom adaptativo" (activado por defecto)
- **CLI**: Flag `--adaptive-crop`

## 🚀 Uso

### Opción 1: Interfaz Gráfica (Recomendado)

1. Abre la aplicación: `python dancer_tracking_ui.py`
2. Carga tu video y haz el tracking
3. En la sección "Configuración de Export", selecciona:
   - **Formato de video**: `📱 Instagram (4:5) - 1080x1350`
   - ✅ **Zoom adaptativo** (evita que se corten los bailarines) - Activado por defecto
4. Click en "🎬 Exportar Video"

### Opción 2: Línea de Comandos

```bash
# Exportar en formato Instagram CON zoom adaptativo (RECOMENDADO)
python export_final.py IMG_3048_con_Arjona.mov coords_yolo_combined.csv output_instagram.mov --aspect-ratio instagram --adaptive-crop

# Exportar sin zoom adaptativo (modo fijo, puede cortar)
python export_final.py IMG_3048_con_Arjona.mov coords_yolo_combined.csv output_instagram.mov --aspect-ratio instagram

# Con suavizado personalizado
python export_final.py video.mov coords.csv output.mov --aspect-ratio instagram --adaptive-crop --smooth 45

# Con margen personalizado
python export_final.py video.mov coords.csv output.mov --aspect-ratio instagram --adaptive-crop --margin 1.3
```

## 🎨 Formatos Disponibles

| Formato | Aspect Ratio | Resolución | Comando |
|---------|--------------|------------|---------|
| **Instagram** | 4:5 | 1080x1350 | `--aspect-ratio instagram` |
| Cuadrado | 1:1 | 1080x1080 | `--aspect-ratio square` |
| iPhone Vertical | 9:16 | 1080x1920 | `--aspect-ratio 9:16` |
| Horizontal | 16:9 | 1920x1080 | `--aspect-ratio 16:9` |
| Automático | variable | variable | `--aspect-ratio auto` (default) |
| Personalizado | X:Y | calculado | `--aspect-ratio 3:4` |

## 📐 Conversión de Formatos

Tu video actual:
- **Fuente**: 2160x3840 (9:16) - iPhone vertical
- **Instagram**: 1080x1350 (4:5)

**¿Qué sucede en la conversión?**
- El video se hace **menos vertical** (más ancho proporcionalmente)
- Se **recorta arriba/abajo** del video original
- Los bailarines se mantienen **centrados y visibles**
- Solo cambia el encuadre del fondo

```
Antes (9:16)      Después (4:5)
   |█|              |████|
   |█|              |████|
   |█|              |████|
   |█|
   |█|
(muy vertical)   (menos vertical)
```

## ⚙️ Parámetros Opcionales

- `--margin FACTOR`: Margen alrededor de bailarines (default: 1.5)
  - Valores menores = crop más ajustado
  - Valores mayores = más espacio alrededor

- `--smooth WINDOW`: Ventana de suavizado (default: 15 para CSRT, 45 para YOLO)
  - Valores menores = más responsive, más jittery
  - Valores mayores = más suave, más latencia

## 💡 Consejos

1. **Para Instagram posts**: Usa `instagram` o `4:5`
2. **Para Instagram Stories**: Usa `9:16` (mantiene el formato iPhone)
3. **Si los bailarines se cortan**: Reduce el `--margin` a 1.2 o 1.3
4. **Para videos muy movidos**: Aumenta el `--smooth` a 50 o 60

## 🎥 Ejemplo Completo

```bash
# Configuración óptima para Instagram con YOLO tracking
python export_final.py \
    IMG_3048_con_Arjona.mov \
    coords_yolo_combined.csv \
    video_instagram.mov \
    --aspect-ratio instagram \
    --smooth 45 \
    --margin 1.4
```

## ✅ Verificación

Después de exportar, verifica:
1. **Resolución**: 1080x1350 para Instagram
2. **Aspect ratio**: 0.800 (4:5)
3. **Bailarines visibles**: Centrados sin cortes
4. **Audio**: Preservado del video original

```bash
# Verificar dimensiones
python -c "import cv2; v = cv2.VideoCapture('output_instagram.mov'); print(f'{int(v.get(3))}x{int(v.get(4))}')"
```
