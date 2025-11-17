"""
Script de diagnóstico para verificar las diferencias entre videos.
Genera comparaciones visuales lado a lado para validar los resultados.
"""

import cv2
import numpy as np
from pathlib import Path

def extract_common_region(frame_original, target_width, target_height):
    """Extrae la región del frame original que corresponde al crop 4:5."""
    h_orig, w_orig = frame_original.shape[:2]

    # Calcular dimensiones del crop 4:5 centrado
    crop_height = int(w_orig * 5 / 4)

    if crop_height > h_orig:
        crop_height = h_orig
        crop_width = int(h_orig * 4 / 5)
    else:
        crop_width = w_orig

    # Centrar el crop
    x_start = (w_orig - crop_width) // 2
    y_start = (h_orig - crop_height) // 2

    # Extraer región
    cropped = frame_original[y_start:y_start+crop_height, x_start:x_start+crop_width]

    # Redimensionar a la resolución objetivo
    resized = cv2.resize(cropped, (target_width, target_height), interpolation=cv2.INTER_LANCZOS4)

    return resized

def analyze_color_differences(img1, img2):
    """Analiza diferencias de color y brillo entre dos imágenes."""
    # Convertir a LAB para análisis de color
    lab1 = cv2.cvtColor(img1, cv2.COLOR_BGR2LAB)
    lab2 = cv2.cvtColor(img2, cv2.COLOR_BGR2LAB)

    # Calcular promedios por canal
    l1, a1, b1 = cv2.split(lab1)
    l2, a2, b2 = cv2.split(lab2)

    results = {
        'brightness_diff': np.mean(l1) - np.mean(l2),
        'brightness_1': np.mean(l1),
        'brightness_2': np.mean(l2),
        'a_diff': np.mean(a1) - np.mean(a2),
        'b_diff': np.mean(b1) - np.mean(b2),
    }

    return results

def diagnose_videos(video1_path, video2_path, num_samples=5):
    """Genera diagnóstico visual de las diferencias."""
    print("=" * 80)
    print("DIAGNOSTICO VISUAL - COMPARACION DE VIDEOS")
    print("=" * 80)

    cap1 = cv2.VideoCapture(str(video1_path))
    cap2 = cv2.VideoCapture(str(video2_path))

    if not cap1.isOpened() or not cap2.isOpened():
        print("ERROR: No se pudieron abrir los videos")
        return

    fps1 = cap1.get(cv2.CAP_PROP_FPS)
    total_frames1 = int(cap1.get(cv2.CAP_PROP_FRAME_COUNT))
    total_frames2 = int(cap2.get(cv2.CAP_PROP_FRAME_COUNT))
    width2 = int(cap2.get(cv2.CAP_PROP_FRAME_WIDTH))
    height2 = int(cap2.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Seleccionar frames distribuidos uniformemente
    sample_frames = np.linspace(0, min(total_frames1, total_frames2) - 1, num_samples, dtype=int)

    # Crear directorio para comparaciones
    output_dir = Path("comparison_frames")
    output_dir.mkdir(exist_ok=True)

    print(f"\nGenerando {num_samples} comparaciones visuales...")
    print(f"Las imagenes se guardaran en: {output_dir}/")
    print("-" * 80)

    brightness_diffs = []
    color_a_diffs = []
    color_b_diffs = []

    for i, frame_num in enumerate(sample_frames):
        cap1.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        cap2.set(cv2.CAP_PROP_POS_FRAMES, frame_num)

        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()

        if not ret1 or not ret2:
            continue

        # Extraer región común del original
        frame1_cropped = extract_common_region(frame1, width2, height2)

        # Analizar diferencias de color
        color_diff = analyze_color_differences(frame1_cropped, frame2)
        brightness_diffs.append(color_diff['brightness_diff'])
        color_a_diffs.append(color_diff['a_diff'])
        color_b_diffs.append(color_diff['b_diff'])

        # Crear comparación lado a lado
        comparison = np.hstack([frame1_cropped, frame2])

        # Añadir texto
        h, w = comparison.shape[:2]
        text_area = np.zeros((60, w, 3), dtype=np.uint8)

        cv2.putText(text_area, f"Frame {frame_num} - Original (izq) vs Procesado (der)",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(text_area, f"Brillo: Orig={color_diff['brightness_1']:.1f} Proc={color_diff['brightness_2']:.1f} Diff={color_diff['brightness_diff']:.1f}",
                   (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        final_image = np.vstack([text_area, comparison])

        # Guardar imagen
        output_path = output_dir / f"comparison_frame_{frame_num:05d}.jpg"
        cv2.imwrite(str(output_path), final_image, [cv2.IMWRITE_JPEG_QUALITY, 95])

        # Calcular PSNR para este frame
        psnr = cv2.PSNR(frame1_cropped, frame2)

        timestamp = frame_num / fps1
        print(f"Frame {frame_num:5d} (t={timestamp:6.1f}s): PSNR={psnr:5.2f} dB, "
              f"Brillo Diff={color_diff['brightness_diff']:6.2f}")

    cap1.release()
    cap2.release()

    print("\n" + "=" * 80)
    print("ANALISIS DE DIFERENCIAS DE COLOR/BRILLO")
    print("=" * 80)

    avg_brightness_diff = np.mean(brightness_diffs)
    avg_a_diff = np.mean(color_a_diffs)
    avg_b_diff = np.mean(color_b_diffs)

    print(f"\nDiferencia promedio de BRILLO (L* en LAB): {avg_brightness_diff:.2f}")
    if abs(avg_brightness_diff) > 5:
        print(f"  ADVERTENCIA: Hay diferencia significativa de brillo!")
        if avg_brightness_diff > 0:
            print(f"  -> El video procesado es mas OSCURO en promedio")
        else:
            print(f"  -> El video procesado es mas BRILLANTE en promedio")
    else:
        print(f"  OK: Diferencia de brillo aceptable")

    print(f"\nDiferencia promedio canal A (verde-rojo): {avg_a_diff:.2f}")
    print(f"Diferencia promedio canal B (azul-amarillo): {avg_b_diff:.2f}")

    if abs(avg_a_diff) > 3 or abs(avg_b_diff) > 3:
        print("\n  ADVERTENCIA: Hay diferencias de color significativas!")
        print("  Esto puede explicar valores bajos de PSNR")

    print("\n" + "=" * 80)
    print("CONCLUSION DEL DIAGNOSTICO")
    print("=" * 80)

    print(f"\n1. Se generaron {num_samples} comparaciones visuales en '{output_dir}/'")
    print("   Revisa estas imagenes para validar visualmente las diferencias")

    print("\n2. Factores que afectan el PSNR:")
    if abs(avg_brightness_diff) > 5:
        print(f"   - Diferencia de brillo: {avg_brightness_diff:.1f} (SIGNIFICATIVA)")
    else:
        print(f"   - Diferencia de brillo: {avg_brightness_diff:.1f} (minima)")

    if abs(avg_a_diff) > 3 or abs(avg_b_diff) > 3:
        print(f"   - Diferencias de color: SI (a={avg_a_diff:.1f}, b={avg_b_diff:.1f})")
    else:
        print(f"   - Diferencias de color: Minimas")

    print("   - Compresion de video: Presente")
    print("   - Reduccion de resolucion: Presente (interpolacion)")

    print("\n3. Recomendaciones:")
    print("   - Abre las imagenes en 'comparison_frames/' para validar visualmente")
    print("   - Compara lado a lado para ver diferencias reales")
    print("   - Si las imagenes se ven similares a pesar del PSNR bajo,")
    print("     las diferencias de color/brillo son la causa principal")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    video_original = Path("IMG_3048_con_Arjona.mov")
    video_procesado = Path("instagram_final.mov")

    if not video_original.exists() or not video_procesado.exists():
        print("ERROR: Videos no encontrados")
        exit(1)

    # Generar 10 muestras distribuidas en el video
    diagnose_videos(video_original, video_procesado, num_samples=10)
