# 🎬 Dancer Tracking & Auto-Crop

Sistema completo para seguir y recortar automáticamente bailarines en videos, **sin GPU** y preservando la calidad original.

**✨ NUEVO:** Interfaz gráfica tipo editor de video - ¡No más línea de comandos!

---

## 🚀 Inicio Rápido

### 1. Instalación (primera vez)

**Requisito:** Python 3.7+
- Descargar: https://www.python.org/downloads/
- ⚠️ **IMPORTANTE:** Marcar "Add Python to PATH" durante la instalación

### 2. Uso - Interfaz Gráfica (RECOMENDADO)

**Doble-click en:**
```
start_ui.bat
```

La interfaz gráfica incluye:
- 🎥 **Reproductor de video integrado** con controles tipo editor
- ⏯️ **Controles de reproducción:** Play, Pause, Frame-by-frame, saltos temporales
- 📊 **Timeline visual** con estado de tracking por frame
- 🎯 **Tracking interactivo** en tiempo real con indicadores de calidad
- ⚙️ **Configuración visual** con sliders y dropdowns
- 🎬 **Export con un click** y barra de progreso
- ⌨️ **Keyboard shortcuts:** Espacio, R, ESC, flechas, A/D

### 3. Uso - Línea de Comandos (Avanzado)

**Doble-click en:**
```
dancer_tracking.bat
```

El script maestro te guiará paso a paso:
- ✅ Instala dependencias automáticamente
- ✅ Instala FFmpeg si es necesario
- ✅ Te permite trackear o usar coordenadas existentes
- ✅ Exporta el video final con alta calidad

---

## 📋 Características

- **Tracking mejorado:** Visualización en tiempo real con detección de problemas
- **Re-inicialización:** Presiona 'R' durante el tracking para re-seleccionar
- **Sin deformación:** Mantiene el aspect ratio correcto
- **Audio preservado:** El video final incluye el audio original
- **Alta calidad:** Exporta con CRF 18 (casi sin pérdida)
- **Sin GPU:** Todo funciona en CPU

---

## 🎯 Flujo de Trabajo

### Opción 1: Todo Automático (Recomendado)
```
dancer_tracking.bat
```
Sigue las instrucciones en pantalla.

### Opción 2: Paso a Paso Manual

#### 1. Verificar video
```powershell
python check_video.py ruta/al/video.mov
```

#### 2. Tracking
```powershell
python track_improved.py video.mov coords.csv --start-time 30 --tracker KCF
```

**Durante el tracking:**
- **Verde** = Tracking OK
- **Naranja** = Advertencia (rectángulo se encoge)
- **Rojo** = Problema detectado
- **R** = Re-inicializar
- **ESPACIO** = Pausar/Reanudar
- **ESC** = Detener

#### 3. Analizar resultados (opcional)
```powershell
python analyze_tracking.py coords.csv
```
Genera estadísticas y gráficos.

#### 4. Exportar
```powershell
python export_final.py video.mov coords.csv output.mov --margin 1.5 --smooth 10
```

---

## ⚙️ Parámetros

### Tracking

**--start-time SEGUNDOS**
- Momento en que comienza el tracking
- Usar cuando el segundo bailarín aparece más tarde
- Ejemplo: `--start-time 30` (empieza a los 30 segundos)

**--tracker TIPO**
- `KCF` (recomendado) - Más estable
- `CSRT` - Muy preciso pero puede fallar
- `MOSSE` - Muy rápido
- `MIL` - Buen balance

### Export

**--margin FACTOR**
- Espacio alrededor de los bailarines
- `1.0` = Ajustado (solo bailarines)
- `1.5` = Cómodo (recomendado)
- `2.0` = Amplio

**--smooth VENTANA**
- Suavizado de movimientos
- `5` = Mínimo suavizado
- `10` = Normal (recomendado)
- `15` = Muy suave

---

## 🛠️ Solución de Problemas

### Error: "Python not found"
- Instala Python desde python.org
- Asegúrate de marcar "Add Python to PATH"

### Error: "Video not found"
- Copia el video a la carpeta `dancer_tracking`
- O especifica la ruta completa

### Error: "FFmpeg not found"
- El script instala FFmpeg automáticamente
- Si falla, descarga manual: https://www.gyan.dev/ffmpeg/builds/

### Tracking se pierde
- Presiona **R** durante el tracking para re-seleccionar
- Usa un rectángulo más grande al inicio
- Prueba el tracker **KCF** en lugar de CSRT
- Especifica `--start-time` cuando ambos bailarines estén visibles

### Video deformado
- Esto está corregido en la versión actual
- Si persiste, reporta el problema

### Audio desincronizado
- El script exporta el video completo desde el inicio
- Audio siempre sincronizado

---

## 🖥️ Interfaz Gráfica - Guía de Uso

### Workflow en la UI

1. **Cargar Video**
   - Click en "Abrir Video..."
   - Selecciona tu archivo de video
   - Opcionalmente cambia el audio con "Cambiar Audio..."
   - Puedes usar coordenadas existentes marcando el checkbox

2. **Configurar Tracking**
   - Selecciona el tipo de tracker (KCF recomendado)
   - Indica si ambos bailarines están visibles desde el inicio
   - Si no, especifica el tiempo de inicio en segundos
   - Click en "🎯 Seleccionar Área"

3. **Tracking Interactivo**
   - Dibuja un rectángulo alrededor de los bailarines
   - Presiona **Espacio** o **Reanudar** para iniciar el tracking
   - **Verde** = Tracking OK
   - **Naranja** = Advertencia
   - **Rojo** = Problema - presiona R para re-seleccionar el área
   - **Pausa y navegación libre:**
     - Presiona **Espacio** para pausar el tracking
     - Navega libremente con flechas, botones o timeline
     - El rectángulo se mantiene visible como referencia
     - Presiona **Espacio** o **Reanudar** para continuar desde donde estés
   - Si el tracking se pierde, presiona **R** para volver a dibujar el rectángulo
   - Después de re-dibujar, presiona **Espacio** o **Reanudar** para continuar
   - Los frames ya trackeados se saltan automáticamente (no se trackean dos veces)

4. **Configurar Export**
   - Ajusta el margen con el slider (1.0-2.5x)
   - Ajusta el suavizado con el slider (5-30 frames)
   - Especifica el nombre del archivo de salida
   - Click en "Exportar Video"

5. **Ver Resultado**
   - Espera a que termine la exportación
   - La UI te preguntará si quieres abrir la carpeta
   - ¡Listo!

### Keyboard Shortcuts

| Tecla | Función |
|-------|---------|
| **Espacio** | Pausar/Reanudar tracking (o Play/Pause cuando no hay tracking) |
| **Enter/Intro** | Pausar/Reanudar tracking |
| **←/→** | Frame anterior/siguiente (±1 frame) |
| **A/D** | Saltar ±10 frames |
| **W/S** | Saltar ±5 segundos |
| **R** | Re-seleccionar área (durante tracking) |
| **ESC** | Detener tracking |

**Nota:** Los atajos de teclado coinciden con el script original `track_improved.py`. También hay botones adicionales para navegación más precisa (±1 frame, ±1 segundo).

### Componentes de la UI

- **Panel superior:** Carga de archivos y video info
- **Reproductor central:** Video con overlay de tracking
- **Controles de reproducción:** Play, pause, navegación, velocidad
- **Timeline:** Visualización del estado por frame con zoom
- **Panel derecho:** Configuración de tracking y export
- **Log:** Mensajes y estado de las operaciones

## 📂 Estructura del Proyecto

```
dancer_tracking/
├── README.md                    # Este archivo
├── requirements.txt             # Dependencias Python
│
├── start_ui.bat                 # LAUNCHER UI (RECOMENDADO)
├── dancer_tracking.bat          # Script consola (alternativo)
│
├── dancer_tracking_ui.py        # Aplicación principal de la UI
├── video_player.py              # Widget de video player
├── timeline_widget.py           # Widget de timeline
├── tracking_thread.py           # Thread de tracking
├── export_thread.py             # Thread de export
├── test_ui.py                   # Test de imports de UI
│
├── track_improved.py            # Tracking con detección de problemas
├── export_final.py              # Export final con calidad preservada
├── analyze_tracking.py          # Analizar coordenadas
├── check_video.py               # Verificar compatibilidad del video
├── test_installation.py         # Test de instalación
│
├── install_ffmpeg.ps1           # Instalador automático de FFmpeg
├── convert_video.bat            # Conversión manual (opcional)
│
├── coords.csv                   # Coordenadas del tracking (generado)
│
├── ffmpeg/                      # FFmpeg (auto-instalado)
└── venv/                        # Entorno virtual (auto-creado)
```

---

## 💡 Consejos

### Para mejores resultados de tracking:

1. **Selecciona un rectángulo GRANDE** al inicio
   - Incluye espacio alrededor de los bailarines
   - Más contexto = tracking más estable

2. **Usa --start-time cuando sea apropiado**
   - Si solo hay un bailarín al inicio, empieza cuando aparezcan ambos
   - Ejemplo: `--start-time 30`

3. **Vigila el tracking en tiempo real**
   - Si se vuelve rojo → presiona **R** inmediatamente
   - Re-selecciona y continúa

4. **Prueba diferentes trackers**
   - KCF suele ser más estable que CSRT
   - Cada video es diferente

5. **Conserva coords.csv**
   - Puedes re-exportar con diferentes parámetros
   - No necesitas re-trackear

---

## 📊 Rendimiento Esperado

Para un video de **3 minutos a 30 FPS**:

| Etapa | Tiempo | Resultado |
|-------|--------|-----------|
| Tracking | 5-10 min | coords.csv (~200 KB) |
| Export | 2-5 min | video.mov (~500-800 MB) |
| **Total** | **7-15 min** | Video final con audio |

*Tiempos en CPU moderno sin GPU*

---

## 🔧 Comandos Útiles

### Verificar instalación
```powershell
python test_installation.py
```

### Ver información del video
```powershell
python check_video.py video.mov
```

### Analizar tracking existente
```powershell
python analyze_tracking.py coords.csv
```

### Re-exportar con otros parámetros
```powershell
python export_final.py video.mov coords.csv nuevo_output.mov --margin 1.8 --smooth 15
```

---

## 📝 Notas Técnicas

### Tracking
- Usa OpenCV con tracker CSRT o KCF
- Detección automática de pérdida de tracking
- Smoothing con ventana móvil

### Export
- Formato: MOV con H.264 (libx264)
- Calidad: CRF 18 (cuasi-lossless)
- Audio: AAC 192k
- Sin deformación: aspect ratio fijo

### Dependencias
- opencv-contrib-python
- numpy
- matplotlib (para análisis)

---

## ❓ FAQ

**P: ¿Necesito GPU?**
R: No, todo funciona en CPU.

**P: ¿Cuánto tarda?**
R: Para un video de 3 min: 7-15 minutos total.

**P: ¿Pierdo calidad?**
R: No, usamos CRF 18 que es casi sin pérdida.

**P: ¿Se preserva el audio?**
R: Sí, siempre.

**P: ¿Qué hago si el tracking falla?**
R: Presiona 'R' durante el tracking para re-seleccionar.

**P: ¿Puedo trackear más de 2 personas?**
R: Actualmente está optimizado para 1-2 bailarines.

**P: ¿Funciona con otros videos?**
R: Sí, con cualquier video compatible con OpenCV.

---

## 🆘 Soporte

Si encuentras problemas:
1. Lee esta documentación completamente
2. Verifica que Python y FFmpeg estén instalados
3. Intenta con `test_installation.py`
4. Revisa los mensajes de error específicos

---

## 📜 Licencia

Libre para uso personal y profesional.

---

**¡Buen tracking! 🎬💃🕺**
