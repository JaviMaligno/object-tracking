"""
Script para comparar objetivamente la calidad de video entre dos archivos.
Compara IMG_3048_con_Arjona.mov (original) con instagram_final.mov (procesado).

Métricas calculadas:
- PSNR (Peak Signal-to-Noise Ratio): >30 dB aceptable, >40 dB excelente
- MSE (Mean Squared Error): Menor = mejor
- Nitidez (Laplacian Variance): Mayor = más nitidez
"""

import cv2
import numpy as np
from pathlib import Path
import sys

def calculate_sharpness(image):
    """Calcula la nitidez usando varianza del Laplaciano."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return laplacian.var()

def calculate_mse(img1, img2):
    """Calcula el Mean Squared Error entre dos imágenes."""
    return np.mean((img1.astype(float) - img2.astype(float)) ** 2)

def extract_common_region(frame_original, target_width, target_height):
    """
    Extrae la región del frame original que corresponde al crop 4:5.

    El video original es 2160x3840 (9:16)
    El video procesado es crop 4:5 centrado
    """
    h_orig, w_orig = frame_original.shape[:2]

    # Calcular dimensiones del crop 4:5 centrado en el original
    # Si mantenemos el ancho original, la altura sería: w * 5/4
    crop_height = int(w_orig * 5 / 4)

    # Si el crop_height es mayor que la altura original, usar ancho como limitante
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

def compare_videos(video1_path, video2_path, sample_interval=2.0):
    """
    Compara dos videos calculando métricas de calidad.

    Args:
        video1_path: Path al video original
        video2_path: Path al video procesado
        sample_interval: Intervalo en segundos entre frames muestreados
    """
    print("=" * 80)
    print("COMPARACIÓN DE CALIDAD DE VIDEO")
    print("=" * 80)
    print(f"\nVideo Original: {video1_path}")
    print(f"Video Procesado: {video2_path}")
    print(f"Intervalo de muestreo: {sample_interval} segundos\n")

    # Abrir videos
    cap1 = cv2.VideoCapture(str(video1_path))
    cap2 = cv2.VideoCapture(str(video2_path))

    if not cap1.isOpened() or not cap2.isOpened():
        print("ERROR: No se pudieron abrir los videos")
        return

    # Obtener propiedades
    fps1 = cap1.get(cv2.CAP_PROP_FPS)
    fps2 = cap2.get(cv2.CAP_PROP_FPS)
    total_frames1 = int(cap1.get(cv2.CAP_PROP_FRAME_COUNT))
    total_frames2 = int(cap2.get(cv2.CAP_PROP_FRAME_COUNT))
    width2 = int(cap2.get(cv2.CAP_PROP_FRAME_WIDTH))
    height2 = int(cap2.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"Video Original: {int(cap1.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap1.get(cv2.CAP_PROP_FRAME_HEIGHT))} @ {fps1:.2f} fps, {total_frames1} frames")
    print(f"Video Procesado: {width2}x{height2} @ {fps2:.2f} fps, {total_frames2} frames")

    # Calcular frames a muestrear
    frame_interval = int(sample_interval * fps1)
    sample_frames = list(range(0, min(total_frames1, total_frames2), frame_interval))

    print(f"\nMuestreando {len(sample_frames)} frames (1 cada {sample_interval}s)...")
    print("-" * 80)

    # Métricas
    psnr_values = []
    mse_values = []
    sharpness_original = []
    sharpness_processed = []

    # Procesar frames
    for i, frame_num in enumerate(sample_frames):
        # Posicionar ambos videos en el mismo frame
        cap1.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        cap2.set(cv2.CAP_PROP_POS_FRAMES, frame_num)

        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()

        if not ret1 or not ret2:
            print(f"Advertencia: No se pudo leer frame {frame_num}")
            continue

        # Extraer región común del original y redimensionar
        frame1_cropped = extract_common_region(frame1, width2, height2)

        # Calcular métricas
        try:
            psnr = cv2.PSNR(frame1_cropped, frame2)
            mse = calculate_mse(frame1_cropped, frame2)
            sharp1 = calculate_sharpness(frame1_cropped)
            sharp2 = calculate_sharpness(frame2)

            psnr_values.append(psnr)
            mse_values.append(mse)
            sharpness_original.append(sharp1)
            sharpness_processed.append(sharp2)

            if (i + 1) % 10 == 0:
                print(f"Procesados {i + 1}/{len(sample_frames)} frames...")

        except Exception as e:
            print(f"Error procesando frame {frame_num}: {e}")
            continue

    cap1.release()
    cap2.release()

    if not psnr_values:
        print("\nERROR: No se pudieron procesar frames")
        return

    # Calcular estadísticas
    print(f"\nCompletado: {len(psnr_values)} frames analizados")
    print("=" * 80)
    print("\nRESULTADOS DE COMPARACIÓN DE CALIDAD")
    print("=" * 80)

    print("\n1. PSNR (Peak Signal-to-Noise Ratio)")
    print("   Interpretación: >40 dB = Excelente, 30-40 dB = Buena, <30 dB = Pérdida notable")
    print(f"   Promedio: {np.mean(psnr_values):.2f} dB")
    print(f"   Mínimo:   {np.min(psnr_values):.2f} dB")
    print(f"   Máximo:   {np.max(psnr_values):.2f} dB")
    print(f"   Desv.Est: {np.std(psnr_values):.2f} dB")

    print("\n2. MSE (Mean Squared Error)")
    print("   Interpretación: Menor = mejor (0 = imágenes idénticas)")
    print(f"   Promedio: {np.mean(mse_values):.2f}")
    print(f"   Mínimo:   {np.min(mse_values):.2f}")
    print(f"   Máximo:   {np.max(mse_values):.2f}")
    print(f"   Desv.Est: {np.std(mse_values):.2f}")

    print("\n3. NITIDEZ (Laplacian Variance)")
    print("   Interpretación: Mayor = más nitidez/detalle")
    avg_sharp_orig = np.mean(sharpness_original)
    avg_sharp_proc = np.mean(sharpness_processed)
    sharpness_loss = ((avg_sharp_orig - avg_sharp_proc) / avg_sharp_orig) * 100

    print(f"   Original:   {avg_sharp_orig:.2f} (promedio)")
    print(f"   Procesado:  {avg_sharp_proc:.2f} (promedio)")
    print(f"   Pérdida:    {sharpness_loss:.2f}%")

    print("\n" + "=" * 80)
    print("INTERPRETACIÓN Y CONCLUSIONES")
    print("=" * 80)

    avg_psnr = np.mean(psnr_values)

    print("\n[*] Calidad de preservacion:")
    if avg_psnr >= 40:
        print(f"  EXCELENTE - PSNR {avg_psnr:.2f} dB indica perdida minima de calidad")
    elif avg_psnr >= 30:
        print(f"  BUENA - PSNR {avg_psnr:.2f} dB indica perdida aceptable de calidad")
    else:
        print(f"  REGULAR - PSNR {avg_psnr:.2f} dB indica perdida notable de calidad")

    print("\n[*] Analisis de nitidez:")
    if sharpness_loss < 5:
        print(f"  Perdida minima de nitidez ({sharpness_loss:.1f}%) - Apenas perceptible")
    elif sharpness_loss < 15:
        print(f"  Perdida moderada de nitidez ({sharpness_loss:.1f}%) - Puede ser perceptible")
    else:
        print(f"  Perdida significativa de nitidez ({sharpness_loss:.1f}%) - Probablemente perceptible")

    print("\n[*] Consideraciones tecnicas:")
    print(f"  - Reduccion de resolucion: {int(cap1.get(cv2.CAP_PROP_FRAME_WIDTH))*int(cap1.get(cv2.CAP_PROP_FRAME_HEIGHT))} -> {width2*height2} pixeles")
    print(f"  - Reduccion de area visible: Crop 9:16 -> 4:5 (Instagram)")
    print(f"  - Compresion adicional aplicada")

    print("\n" + "=" * 80)

    # Guardar resultados detallados
    output_file = "video_quality_comparison.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("RESULTADOS DETALLADOS - COMPARACIÓN DE CALIDAD\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Video Original: {video1_path}\n")
        f.write(f"Video Procesado: {video2_path}\n\n")
        f.write(f"PSNR Promedio: {np.mean(psnr_values):.2f} dB\n")
        f.write(f"MSE Promedio: {np.mean(mse_values):.2f}\n")
        f.write(f"Nitidez Original: {avg_sharp_orig:.2f}\n")
        f.write(f"Nitidez Procesado: {avg_sharp_proc:.2f}\n")
        f.write(f"Pérdida de Nitidez: {sharpness_loss:.2f}%\n\n")
        f.write("VALORES POR FRAME:\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Frame':<8} {'PSNR (dB)':<12} {'MSE':<12} {'Nitidez Orig':<15} {'Nitidez Proc':<15}\n")
        f.write("-" * 80 + "\n")
        for i, frame_num in enumerate(sample_frames[:len(psnr_values)]):
            f.write(f"{frame_num:<8} {psnr_values[i]:<12.2f} {mse_values[i]:<12.2f} "
                   f"{sharpness_original[i]:<15.2f} {sharpness_processed[i]:<15.2f}\n")

    print(f"\n[*] Resultados detallados guardados en: {output_file}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    # Rutas a los videos
    video_original = Path("IMG_3048_con_Arjona.mov")
    video_procesado = Path("instagram_final.mov")

    # Verificar existencia
    if not video_original.exists():
        print(f"ERROR: No se encuentra {video_original}")
        sys.exit(1)

    if not video_procesado.exists():
        print(f"ERROR: No se encuentra {video_procesado}")
        sys.exit(1)

    # Ejecutar comparación
    compare_videos(video_original, video_procesado, sample_interval=2.0)
