#!/usr/bin/env python3
"""
process_video.py - Script todo-en-uno

Combina track_yolo.py y export_final.py para procesar un video de principio a fin.
Ejecuta el tracking (si no existen las coordenadas) y luego la exportación.
"""

import os
import sys
import argparse
from pathlib import Path

# Importar módulos existentes
from track_yolo import YOLODancerTracker
from export_final import crop_and_export_fixed_ratio

def main():
    parser = argparse.ArgumentParser(description="Procesa un video: Tracking + Exportación Automática")
    
    # Argumentos obligatorios
    parser.add_argument("video_path", help="Ruta al archivo de video (ej: data/video.mov)")
    
    # Argumentos opcionales de salida
    parser.add_argument("--output", "-o", help="Ruta del video de salida (default: outputs/nombre_video_final.mov)")
    
    # Argumentos de Tracking
    parser.add_argument("--force-track", action="store_true", help="Forzar tracking incluso si ya existen coordenadas")
    parser.add_argument("--model", default="n", choices=["n", "s", "m"], help="Tamaño del modelo YOLO (n=nano, s=small)")
    
    # Argumentos de Exportación
    parser.add_argument("--aspect-ratio", "-ar", default="instagram", help="Ratio de aspecto (instagram, 9:16, 16:9, auto)")
    parser.add_argument("--adaptive-crop", action="store_true", default=True, help="Usar crop adaptativo (recomendado)")
    parser.add_argument("--no-adaptive", action="store_false", dest="adaptive_crop", help="Desactivar crop adaptativo")
    parser.add_argument("--margin", type=float, default=1.5, help="Margen alrededor del bailarín (default: 1.5)")
    parser.add_argument("--smooth", type=int, default=15, help="Ventana de suavizado (default: 15)")
    
    args = parser.parse_args()
    
    # 1. Configuración de Rutas
    video_path = Path(args.video_path)
    if not video_path.exists():
        print(f"❌ Error: El video '{video_path}' no existe.")
        return 1
        
    # Definir rutas de salida automáticas si no se especifican
    video_stem = video_path.stem
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    
    # Rutas de archivos intermedios
    coords_csv = output_dir / f"{video_stem}_coords.csv"
    combined_csv = output_dir / f"{video_stem}_coords_combined.csv"
    
    # Ruta final
    if args.output:
        final_video_path = Path(args.output)
    else:
        final_video_path = output_dir / f"{video_stem}_final.mov"
    
    # Asegurar que el directorio de salida final existe
    final_video_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"🎥 Procesando: {video_path}")
    print(f"📂 Salida: {final_video_path}")
    print("-" * 50)
    
    # 2. TRACKING (Paso 1)
    # Verificar si ya tenemos coordenadas para ahorrar tiempo (a menos que --force-track esté activo)
    has_coords = combined_csv.exists()
    
    if has_coords and not args.force_track:
        print(f"ℹ️  Coordenadas encontradas en '{combined_csv}'")
        print("   Saltando tracking (usa --force-track para re-procesar)")
    else:
        print("🚀 PASO 1: Tracking de bailarines (YOLOv8)...")
        try:
            tracker = YOLODancerTracker(
                video_path=str(video_path),
                model_size=args.model,
                tracker_type="botsort",
                conf_threshold=0.3
            )
            
            tracker.track_video()
            
            # Guardar CSVs
            tracker.save_coords_csv(str(coords_csv), mode="individual")
            tracker.save_coords_csv(str(combined_csv), mode="combined")
            
        except Exception as e:
            print(f"❌ Error durante el tracking: {e}")
            import traceback
            traceback.print_exc()
            return 1
            
    # 3. EXPORTACIÓN (Paso 2)
    print("\n" + "-" * 50)
    print("🚀 PASO 2: Exportación y Crop...")
    
    try:
        success = crop_and_export_fixed_ratio(
            video_path=str(video_path),
            coords_csv=str(combined_csv),
            output_path=str(final_video_path),
            margin_factor=args.margin,
            smooth_window=args.smooth,
            aspect_ratio=args.aspect_ratio,
            adaptive_crop=args.adaptive_crop
        )
        
        if success:
            print("\n✨ PROCESO COMPLETADO EXITOSAMENTE ✨")
            print(f"   Video guardado en: {final_video_path}")
            return 0
        else:
            print("\n❌ Error durante la exportación")
            return 1
            
    except Exception as e:
        print(f"❌ Error durante la exportación: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

