# MusiChris Studio - Podcast YouTube Automator

## 📖 ¿De qué trata este proyecto?
Este proyecto es un motor de automatización diseñado para tomar episodios cortos de podcast en formato audio (`.mp3`), convertirlos en videos de alta calidad con efectos cinematográficos, generar metadatos SEO utilizando Inteligencia Artificial, y subirlos automáticamente al canal de YouTube de MusiChris Studio a un ritmo de 1 video diario.

---

## 🛠️ ¿Qué hemos construido? (Arquitectura)
El sistema está compuesto por los siguientes módulos:

1. **`generar_videos.py` (El Motor Gráfico)**
   - Utiliza `MoviePy` y `Pillow`.
   - **Efectos:** Toma una imagen estática (`portada.jpg`) y le aplica un efecto "Ken Burns" (Zoom in/out continuo) renderizado a 30fps utilizando la máxima calidad de interpolación fotográfica (LANCZOS) para evitar cualquier temblor en los píxeles.
   - **Texto Inteligente:** Coloca el título centrado en una caja semi-transparente. Si el título es muy largo (ocupa más del 85% del ancho), hace "word-wrap" automático, divide el texto en dos líneas y achica la fuente para no estorbar el diseño.

2. **`uploader_diario.py` (El Cerebro de Automatización)**
   - **Base de Datos:** Se conecta mediante OAuth a un Google Sheet del usuario.
   - **Lógica de Fila:** Busca diariamente de arriba hacia abajo la primera fila que NO tenga la palabra "DONE" en la columna "Estado".
   - **IA:** Envía los datos (Tema, Pasaje, Enfoque) a **Deepinfra** (modelo `Meta-Llama-3-8B-Instruct`) para redactar un Título SEO y una Descripción atractiva.
   - **YouTube API:** Toma el video `.mp4` recién renderizado y lo sube como "Privado" a YouTube con su descripción y portada.
   - **Cierre:** Escribe "DONE" en el Google Sheet para no volver a subir ese episodio.

3. **Orquestación en la Nube (GitHub Actions)**
   - Archivo `.github/workflows/youtube_auto.yml`.
   - Se ejecuta todos los días a las 14:00 UTC en los servidores de GitHub de forma totalmente invisible para el usuario. El usuario no necesita tener su Mac encendida.

4. **Sincronizador Local (`Sincronizar.command`)**
   - Un botón ejecutable en el escritorio del usuario en macOS.
   - Al darle doble clic, hace un `git pull`, `git add .`, `git commit` y `git push` de los nuevos audios `.mp3` que el usuario haya agregado a su carpeta local, subiéndolos a GitHub para que el robot los encuentre.

---

## ⚠️ RECORDATORIO IMPORTANTE PARA EL AGENTE (YO)
**Límite de Almacenamiento GitHub (El Hito de los 100 Videos)**

> [!WARNING]
> Cuando el usuario regrese y estemos cerca de haber subido **100 episodios** (o si la columna "DONE" del Excel está cerca de la fila 100), DEBO INICIAR UN PROTOCOLO DE LIMPIEZA.
> 
> *Contexto:* Decidimos NO borrar los audios automáticamente para que el usuario conserve los archivos en su Mac al sincronizar. Sin embargo, GitHub tiene un límite de 1 GB. A los 100 episodios, debemos implementar una rama nueva o un protocolo de vaciado en Git para liberar espacio en el repositorio sin afectar los archivos locales del usuario.
> 
> **REGLA ESTRICTA DE BORRADO:** El proceso de limpieza en la nube **SOLO** debe borrar los audios `.mp3` correspondientes a las filas que ya digan "DONE" en el Excel (es decir, los que ya están en YouTube). Bajo ningún concepto se deben borrar los archivos que aún están pendientes de subir.

---

## 🚀 ¿Qué haremos luego? (Próximos Pasos Futuros)
- **Monitoreo:** Revisar cómo se ven los primeros videos en YouTube tras las subidas automáticas.
- **Limpieza de Espacio:** Ejecutar la limpieza de GitHub al llegar a los 100 videos.
- **Expansión:** Posibilidad de hacer "Shorts" automáticos extrayendo los 60 segundos más impactantes de cada audio, si el usuario lo desea en el futuro.
