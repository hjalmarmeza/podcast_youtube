import os
import re
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import AudioFileClip, ImageClip, CompositeVideoClip, VideoClip
import pandas as pd

BASE_DIR = '/Users/hjalmarmeza/Downloads/Antigravity/Posible proyecto'
AUDIO_DIR = os.path.join(BASE_DIR, 'Audios de podcast')
OUTPUT_DIR = os.path.join(BASE_DIR, 'Videos_Finales')
FONT_PATH = os.path.join(BASE_DIR, 'Montserrat-Bold.ttf')
CSV_PATH = os.path.join(BASE_DIR, 'metadata.csv')

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def get_clean_title(filename):
    name = os.path.splitext(filename)[0]
    name = re.sub(r'^\d+\._?', '', name)
    name = name.replace('_', ' ')
    return name.strip()

def create_text_overlay(image_path, text, output_path):
    with Image.open(image_path) as ref_img:
        img_width, img_height = ref_img.size
        
    overlay = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Intentar fuente normal (8% de altura)
    base_font_size = int(img_height * 0.08)
    try:
        font = ImageFont.truetype(FONT_PATH, base_font_size)
    except IOError:
        font = ImageFont.load_default()
        
    max_text_width = img_width * 0.85 # Maximo 85% del ancho de la imagen
    
    # Lógica para envolver el texto (Word Wrap)
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        w = draw.textbbox((0, 0), " ".join(current_line), font=font)[2]
        if w > max_text_width:
            if len(current_line) > 1:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(" ".join(current_line))
                current_line = []
    if current_line:
        lines.append(" ".join(current_line))
        
    # Si hay más de una línea, reducimos el tamaño de la fuente al 6% para que no tape tanto fondo
    if len(lines) > 1:
        base_font_size = int(img_height * 0.06)
        try:
            font = ImageFont.truetype(FONT_PATH, base_font_size)
        except IOError:
            font = ImageFont.load_default()
            
    # Calcular altura total y ancho máximo
    total_text_height = 0
    max_line_width = 0
    line_spacing = int(base_font_size * 0.2)
    line_bboxes = []
    
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        if lw > max_line_width:
            max_line_width = lw
        total_text_height += lh + line_spacing
        line_bboxes.append((lw, lh))
        
    total_text_height -= line_spacing # quitar el ultimo espacio
    
    # Coordenadas base
    x_center = img_width / 2
    y_base = img_height - (img_height * 0.15) - total_text_height # Margen inferior del 15%
    
    # Dibujar la caja negra semi-transparente
    padding_x = int(img_width * 0.05)
    padding_y = int(img_height * 0.02)
    box_x0 = max(0, x_center - (max_line_width/2) - padding_x)
    box_y0 = max(0, y_base - padding_y)
    box_x1 = min(img_width, x_center + (max_line_width/2) + padding_x)
    box_y1 = min(img_height, y_base + total_text_height + padding_y)
    
    draw.rectangle([box_x0, box_y0, box_x1, box_y1], fill=(0, 0, 0, 180))
    
    # Dibujar los textos línea por línea
    current_y = y_base
    shadow_offset = max(2, int(base_font_size * 0.04))
    
    for i, line in enumerate(lines):
        lw, lh = line_bboxes[i]
        line_x = x_center - (lw / 2)
        
        # Sombra
        draw.text((line_x + shadow_offset, current_y + shadow_offset), line, font=font, fill=(0, 0, 0, 255))
        # Texto
        draw.text((line_x, current_y), line, font=font, fill=(255, 255, 255, 255))
        
        current_y += lh + line_spacing
        
    overlay.save(output_path, format="PNG")
    return output_path

# Creador de clip animado anti-temblor usando PIL Lanczos
def make_smooth_zoom_clip(image_path, duration, zoom_max=0.15, ciclo_segundos=15.0):
    img = Image.open(image_path).convert("RGB")
    W, H = img.size
    
    def make_frame(t):
        # Onda que oscila suavemente entre 0 y 1 cada 'ciclo_segundos'
        onda = (math.sin(2 * math.pi * t / ciclo_segundos - math.pi/2) + 1) / 2
        scale = 1.0 + zoom_max * onda
        
        # Calcular el cuadro a recortar de la imagen original usando floats
        crop_w = W / scale
        crop_h = H / scale
        
        x0 = (W - crop_w) / 2
        y0 = (H - crop_h) / 2
        x1 = x0 + crop_w
        y1 = y0 + crop_h
        
        # Resize directo desde el crop usando Lanczos (alta calidad, cero temblor)
        try:
            resample_filter = Image.Resampling.LANCZOS
        except AttributeError:
            resample_filter = Image.LANCZOS # Compatibilidad con versiones viejas de Pillow
            
        cropped = img.resize((W, H), box=(x0, y0, x1, y1), resample=resample_filter)
        return np.array(cropped)
        
    return VideoClip(make_frame, duration=duration)

def process_episode(series_name, audio_filename, audio_folder):
    if not audio_filename.endswith('.mp3'):
        return
        
    print(f"\nProcesando: {series_name} -> {audio_filename}")
    
    audio_path = os.path.join(audio_folder, audio_filename)
    cover_path = os.path.join(audio_folder, 'portada.jpg')
    if not os.path.exists(cover_path):
        # Buscar cualquier jpg o png en la carpeta
        imgs = [f for f in os.listdir(audio_folder) if f.lower().endswith(('.jpg', '.png'))]
        if not imgs:
            print(f"Error: No se encontró imagen de portada en {audio_folder}")
            return
        cover_path = os.path.join(audio_folder, imgs[0])
        
    series_out_dir = os.path.join(OUTPUT_DIR, series_name)
    if not os.path.exists(series_out_dir):
        os.makedirs(series_out_dir)
        
    title = get_clean_title(audio_filename)
    
    temp_text_path = os.path.join(series_out_dir, f"temp_text_{title}.png")
    create_text_overlay(cover_path, title, temp_text_path)
    
    output_mp4 = os.path.join(series_out_dir, f"{title}.mp4")
    
    try:
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        # Generar fondo animado sin temblores (anti-aliasing)
        animated_bg = make_smooth_zoom_clip(cover_path, duration)
        
        # Texto estático encima
        text_clip = ImageClip(temp_text_path).with_duration(duration)
        
        # Combinar capas
        final_clip = CompositeVideoClip([animated_bg, text_clip]).with_audio(audio_clip)
        
        final_clip.write_videofile(
            output_mp4, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac",
            preset="ultrafast",
            logger=None
        )
        
        audio_clip.close()
        text_clip.close()
        final_clip.close()
        if os.path.exists(temp_text_path):
            os.remove(temp_text_path)
        
        print(f"ÉXITO: {output_mp4}")
        return output_mp4
    except Exception as e:
        print(f"ERROR procesando {title}: {e}")
        return None

def run_test():
    test_folder = 'Atributos_de_Dios'
    # Probando con un título ficticio muy largo para validar que se divida en dos líneas
    test_file = '1._Dios_Proveedor.mp3'
    audio_dir = os.path.join(AUDIO_DIR, test_folder)
    
    # Renombrar temporalmente solo en memoria para probar titulo largo
    # En producción tomará el nombre real
    if os.path.exists(os.path.join(audio_dir, test_file)):
        process_episode(test_folder, test_file, audio_dir)

if __name__ == '__main__':
    run_test()
