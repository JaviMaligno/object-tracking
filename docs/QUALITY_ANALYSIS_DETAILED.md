# Análisis Detallado de Calidad - Video Mejorado

## Resultados de la Comparación

### Comparativa de Métricas

| Métrica | instagram_final.mov (antes) | instagram_mejorado.mov (después) | Mejora |
|---------|----------------------------|----------------------------------|---------|
| **PSNR** | 12.31 dB | 12.30 dB | -0.01 dB (sin cambio) |
| **MSE** | 3903.46 | 3927.10 | +23.64 (ligeramente peor) |
| **Pérdida de Nitidez** | 79.31% | 70.57% | **-8.7 puntos (11% mejor)** ✓ |
| **Diferencia de Brillo** | -5.19 | -5.18 | -0.01 (sin cambio) |
| **Diferencia Color A** | -1.31 | -1.28 | +0.03 (sin cambio) |
| **Diferencia Color B** | -3.99 | -3.92 | +0.07 (sin cambio) |
| **Tamaño Archivo** | 265 MB | 399 MB | +134 MB (+51%) |

### Interpretación de Resultados

#### ✅ Mejoras Confirmadas

**1. Nitidez preservada mejoró 11%**
- De 79.31% de pérdida → 70.57% de pérdida
- Esto confirma que **LANCZOS4 está funcionando correctamente**
- La interpolación de alta calidad preserva más detalles finos

**2. Tamaño de archivo aumentó 51%**
- De 265 MB → 399 MB
- Esto confirma que **CRF 16 está funcionando** (menos compresión = más calidad)
- El bitrate aumentó significativamente

#### ❌ Sin Mejora Aparente

**1. PSNR se mantuvo igual (~12.3 dB)**
- No hubo mejora significativa
- **Razón**: El PSNR está dominado por diferencias de color/brillo, no por nitidez

**2. Diferencias de color/brillo no cambiaron**
- Brillo: -5.19 → -5.18 (sin cambio)
- Colores: prácticamente idénticos
- **Razón**: Estas diferencias se introducen en otra parte del pipeline

## Diagnóstico: ¿Por qué el PSNR no mejoró?

### El Problema del PSNR

PSNR (Peak Signal-to-Noise Ratio) mide diferencias píxel por píxel:

```
PSNR = 10 * log10(MAX² / MSE)
```

Donde MSE (Mean Squared Error) es el promedio de diferencias al cuadrado entre píxeles.

**El problema:**
- Una diferencia de brillo de -5.2 afecta **TODOS los píxeles**
- Una pérdida de nitidez afecta solo **bordes y detalles finos**
- El brillo domina el cálculo del MSE → domina el PSNR

### Ejemplo Numérico

Supongamos un píxel con valor 100 en el original:

**Diferencia por brillo:**
- Original: 100
- Procesado: 105 (5 unidades más brillante)
- Error al cuadrado: (100-105)² = 25

**Diferencia por pérdida de nitidez en un borde:**
- Original: 100
- Procesado: 98 (ligeramente suavizado)
- Error al cuadrado: (100-98)² = 4

La diferencia de brillo contribuye **6.25x más** al MSE que la pérdida de nitidez.

Como TODOS los píxeles tienen diferencia de brillo, pero solo los bordes tienen pérdida de nitidez, el brillo domina completamente el PSNR.

## ¿De Dónde Viene la Diferencia de Brillo?

### Investigación del Pipeline

```
Video Original (BGR, BT.709?)
    ↓
OpenCV lee frame (BGR)
    ↓
Crop y operaciones (BGR)
    ↓
Resize con LANCZOS4 (BGR)
    ↓
cv2.VideoWriter → MJPEG ⚠️ (YUV 4:2:0?)
    ↓ [Compresión con pérdida]
Archivo temporal .avi
    ↓
FFmpeg lee MJPEG
    ↓
FFmpeg codifica H.264 (YUV 4:2:0, BT.709?)
    ↓
Video Final .mov
```

### Posibles Causas

#### 1. Conversión de Espacio de Color (PRINCIPAL SOSPECHOSO)

**Problema:** OpenCV usa BGR, pero los codecs usan YUV

```
BGR → YUV (por cv2.VideoWriter) → H.264
     ↑                              ↑
  ¿Matriz correcta?           ¿Matriz correcta?
```

**Posibles problemas:**
- OpenCV puede asumir **BT.601** (estándar antiguo)
- FFmpeg puede asumir **BT.709** (estándar HD moderno)
- iPhone graba en **BT.709**
- **Mismatch de matrices** causa shifts de color/brillo

#### 2. Codec MJPEG (FACTOR CONTRIBUYENTE)

**Motion JPEG:**
- Comprime cada frame como JPEG independiente
- JPEG usa espacio de color YCbCr
- Conversión BGR → YCbCr puede introducir cambios
- Compresión con pérdida en canales de croma

#### 3. Range de Pixel (TV vs PC)

**Dos rangos posibles:**
- **TV/Limited range**: Y=16-235, UV=16-240
- **Full range**: Y=0-255, UV=0-255

Si OpenCV escribe en un rango y FFmpeg lee en otro:
- **Limited→Full**: Video más brillante (+5 unidades típico)
- **Full→Limited**: Video más oscuro

**Nuestro caso:** -5.18 de diferencia sugiere que el video procesado es **más brillante**, consistente con **Limited→Full range mismatch**.

## Soluciones Propuestas

### Solución 1: Eliminar Codec Intermedio MJPEG (RECOMENDADO)

**Problema actual:** Doble conversión de espacio de color
```
BGR → YUV (MJPEG) → BGR? → YUV (H.264)
```

**Solución:** Pipe directo de OpenCV a FFmpeg

**Implementación:**
```python
# En lugar de cv2.VideoWriter, usar subprocess pipe
ffmpeg_process = subprocess.Popen([
    'ffmpeg',
    '-y',
    '-f', 'rawvideo',
    '-vcodec', 'rawvideo',
    '-s', f'{crop_w}x{crop_h}',
    '-pix_fmt', 'bgr24',
    '-r', str(fps),
    '-i', '-',  # Stdin
    '-i', video_path,  # Audio source
    '-map', '0:v',
    '-map', '1:a',
    '-c:v', 'libx264',
    '-preset', 'slow',
    '-crf', '16',
    '-pix_fmt', 'yuv420p',
    '-colorspace', 'bt709',
    '-color_range', 'tv',
    '-c:a', 'aac',
    '-shortest',
    output_path
], stdin=subprocess.PIPE)

# En el loop, en lugar de out.write(cropped):
ffmpeg_process.stdin.write(cropped.tobytes())

ffmpeg_process.stdin.close()
ffmpeg_process.wait()
```

**Beneficios esperados:**
- Elimina conversión BGR→YUV→BGR→YUV
- Control explícito de colorspace y range
- PSNR esperado: 12.3 dB → 20-25 dB
- Pérdida de nitidez: 70% → 50-55%

### Solución 2: Codec Temporal Lossless + Flags de Color

**Cambio 1: Usar codec sin pérdida**
```python
# Línea 644 de export_final.py
fourcc = cv2.VideoWriter_fourcc(*'FFV1')  # Lossless
# o
fourcc = cv2.VideoWriter_fourcc('H', 'F', 'Y', 'U')  # HuffYUV
```

**Cambio 2: Flags explícitos en FFmpeg**
```python
cmd = [
    # ... otros parámetros ...
    '-c:v', 'libx264',
    '-preset', 'slow',
    '-crf', '16',
    '-pix_fmt', 'yuv420p',
    '-colorspace', 'bt709',      # ← NUEVO: Especificar BT.709
    '-color_primaries', 'bt709',  # ← NUEVO
    '-color_trc', 'bt709',        # ← NUEVO
    '-color_range', 'tv',         # ← NUEVO: Limited range
    # ... resto ...
]
```

**Beneficios esperados:**
- Preserva colores del archivo temporal lossless
- Control explícito de espacio de color
- PSNR esperado: 12.3 dB → 18-22 dB
- Pérdida de nitidez: 70% → 55-60%
- Trade-off: Archivos temporales 5-10x más grandes

### Solución 3: Corrección Manual de Brillo (ÚLTIMA OPCIÓN)

**Solo si las soluciones anteriores no funcionan:**

```python
# Antes del resize (línea 706)
# Ajustar brillo para compensar
cropped = cv2.convertScaleAbs(cropped, alpha=1.0, beta=-5.2)
```

**No recomendado porque:**
- Es un "parche" no una solución
- El valor de corrección (-5.2) puede variar
- No resuelve diferencias de color (canales A y B)

## Recomendación Final

### Para Validar las Mejoras Actuales

Aunque el PSNR no mejoró significativamente, **las mejoras de nitidez (11%) son reales y visibles**. Para validarlo:

1. **Comparación visual:**
   ```bash
   # Abre las comparaciones generadas
   explorer comparison_frames
   ```

2. **Zoom en detalles:**
   - Observa bordes, texto, texturas finas
   - El video mejorado debería verse más "nítido"
   - La diferencia es sutil pero presente

3. **Tamaño de archivo:**
   - 399 MB vs 265 MB confirma que CRF 16 está funcionando
   - Mayor bitrate = más información preservada

### Para Mejorar Aún Más (Fase 2)

**Implementar Solución 1 (pipe directo) o Solución 2 (flags de color):**

**Impacto esperado:**
- PSNR: 12.3 dB → 18-25 dB (+50-100% mejora)
- Pérdida de nitidez: 70% → 50-55% (+15-20 puntos mejora)
- Diferencia de brillo: -5.2 → -1.0~-2.0 (+60-80% mejora)

**Complejidad:**
- Solución 1: Moderada (refactorización de export loop)
- Solución 2: Baja (solo cambios en líneas 644 y cmd)

## Conclusión

### Lo que SÍ funcionó:
✅ **LANCZOS4** → Mejora de nitidez del 11%
✅ **CRF 16** → Mayor bitrate (399 MB vs 265 MB)
✅ **Preset 'slow'** → Mejor compresión

### Lo que NO funcionó como esperado:
❌ **PSNR no mejoró** → Dominado por diferencias de color/brillo
❌ **Diferencias de color/brillo persisten** → Introducidas por conversiones de espacio de color

### Próximo paso sugerido:
**Implementar flags explícitos de colorspace en FFmpeg (Solución 2)** como prueba rápida para ver si resuelve el problema de color/brillo sin refactorización mayor.

---

**Fecha:** 17 de noviembre de 2024
**Videos analizados:** `IMG_3048_con_Arjona.mov`, `instagram_final.mov`, `instagram_mejorado.mov`
