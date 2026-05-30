import os
import sys
import json
import requests
import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from generar_videos import process_episode

DEEPINFRA_API_KEY = os.environ.get("DEEPINFRA_API_KEY")
YOUTUBE_TOKEN_PATH = "token.json"
YOUTUBE_CREDS_PATH = "credentials.json"
SHEET_ID = "1lOrZJWQs6PjouAPvv4VHHQAUWPu3sPTLpUdyH2wLkFE"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "Audios de podcast")

# Scopes necesarios para YouTube y Google Sheets
SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/spreadsheets"
]

def get_google_credentials():
    creds = None
    if os.path.exists(YOUTUBE_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(YOUTUBE_TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(YOUTUBE_CREDS_PATH):
                raise Exception("Falta credentials.json. Por favor, asegúrate de tenerlo.")
            flow = InstalledAppFlow.from_client_secrets_file(YOUTUBE_CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(YOUTUBE_TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
    return creds

def generate_metadata(serie, tema, pasaje, enfoque):
    if not DEEPINFRA_API_KEY:
        print("Falta DEEPINFRA_API_KEY, usando metadatos por defecto.")
        return f"{tema} | {serie}", f"{enfoque}\n\nPasaje: {pasaje}\n#MusichrisStudio"
        
    url = "https://api.deepinfra.com/v1/openai/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
Eres un experto en YouTube y SEO para contenido cristiano.
Episodio de podcast:
Serie: {serie}
Tema Central: {tema}
Pasaje Principal: {pasaje}
Enfoque: {enfoque}

Genera un Título SEO para YouTube (max 80 chars) y una Descripción (incluyendo llamados a la acción, el pasaje y hashtags). 
Devuelve formato JSON puro con claves: "titulo" y "descripcion".
"""
    data = {
        "model": "meta-llama/Meta-Llama-3-8B-Instruct",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()["choices"][0]["message"]["content"]
        res_json = json.loads(result)
        return res_json.get("titulo", tema), res_json.get("descripcion", enfoque)
    except Exception as e:
        print(f"Error Deepinfra: {e}")
        return f"{tema} | {serie}", f"{enfoque}\n\nPasaje: {pasaje}\n#MusichrisStudio"

def upload_video(youtube, file_path, title, description, thumbnail_path=None):
    print(f"Subiendo a YouTube: {title}")
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "private", 
            "selfDeclaredMadeForKids": False
        }
    }
    
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True)
    )
    
    response = None
    while response is None:
        status, response = insert_request.next_chunk()
        if status:
            print(f"Progreso subida: {int(status.progress() * 100)}%")
            
    video_id = response.get("id")
    print(f"Subida completada. Video ID: {video_id}")
    return video_id

def get_or_create_playlist(youtube, title):
    # Buscar si ya existe la playlist
    request = youtube.playlists().list(part="snippet", mine=True, maxResults=50)
    response = request.execute()
    
    for item in response.get("items", []):
        if item["snippet"]["title"].lower() == title.lower():
            return item["id"]
            
    # Si no existe, crearla
    print(f"Creando nueva Playlist: {title}")
    request = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title},
            "status": {"privacyStatus": "private"}
        }
    )
    response = request.execute()
    return response["id"]

def add_video_to_playlist(youtube, video_id, playlist_id):
    print(f"Añadiendo video a la Playlist...")
    request = youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        }
    )
    request.execute()

def main():
    print("Iniciando Motor de Subida Diaria...")
    creds = get_google_credentials()
    
    # 1. Conectar a Google Sheets
    try:
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).worksheet("Hoja 2")
    except Exception as e:
        print(f"Error conectando a Sheets (¿El token tiene el scope necesario?): {e}")
        return
        
    records = sheet.get_all_records()
    
    # 2. Buscar el primer registro sin "DONE" en la columna de estado
    # Asumiremos que crearemos una columna llamada "Estado" si no existe.
    header = sheet.row_values(1)
    if "Estado" not in header:
        sheet.update_cell(1, len(header) + 1, "Estado")
        estado_col_idx = len(header) + 1
    else:
        estado_col_idx = header.index("Estado") + 1
        
    fila_a_procesar = None
    row_idx = 2
    for row in records:
        estado = str(row.get("Estado", "")).strip().upper()
        if estado != "DONE":
            fila_a_procesar = row
            break
        row_idx += 1
        
    if not fila_a_procesar:
        print("¡No hay videos pendientes por subir! Todos están marcados como DONE.")
        return
        
    serie = fila_a_procesar.get("Serie Temática", "Podcast")
    tema = fila_a_procesar.get("Tema Central", "Enseñanza")
    pasaje = fila_a_procesar.get("Pasaje Clave", "")
    enfoque = fila_a_procesar.get("Enfoque de la Reflexión", "")
    audio_file = "" # No existe esta columna, confiaremos en la búsqueda por Tema Central
    
    # Si la hoja no tiene nombre de archivo exacto, intentamos encontrarlo
    # por convención o deberás agregarlo al sheet. Por ahora asumimos
    # que podemos deducirlo o encontrar el primer mp3 en la carpeta de la serie.
    serie_dir = os.path.join(AUDIO_DIR, serie.replace(" ", "_"))
    if not os.path.exists(serie_dir):
        print(f"No se encontró la carpeta para la serie {serie}")
        return
        
    # Buscar el archivo de audio que coincida o agarrar el primero
    import unicodedata
    def remove_accents(input_str):
        nfkd_form = unicodedata.normalize('NFKD', str(input_str))
        return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

    mp3_files = [f for f in os.listdir(serie_dir) if f.endswith('.mp3')]
    target_mp3 = None
    for f in mp3_files:
        # Remover tildes y convertir a minúsculas
        tema_clean = remove_accents(str(tema)).lower()[:10]
        file_clean = remove_accents(f).lower()
        if tema_clean and tema_clean in file_clean:
            target_mp3 = f
            break
            
    if not target_mp3 and mp3_files:
        # Por seguridad, si no encuentra nombre, ordenar y tratar de deducir por número
        mp3_files.sort() # Asegura que 1, 2, 3 estén en orden
        # Determinar qué número de episodio es en la serie basándonos en cuántos DONE hay en la serie
        # Para ser seguros por ahora, abortamos si no encuentra el archivo exacto
        print(f"Error crítico: No pude encontrar un audio que coincida con '{tema}'. Abortando para no subir el video equivocado.")
        return
        
    if not target_mp3:
        print("No se encontró un audio válido.")
        return
        
    # 3. Generar el Video
    print(f"Generando video para {target_mp3}...")
    output_mp4 = process_episode(serie.replace(" ", "_"), target_mp3, serie_dir)
    
    if not output_mp4 or not os.path.exists(output_mp4):
        print("Error en la generación del video.")
        return
        
    # 4. Generar Metadata con IA
    print("Generando Título y Descripción con IA...")
    title, desc = generate_metadata(serie, tema, pasaje, enfoque)
    
    # 5. Subir a YouTube
    youtube = build("youtube", "v3", credentials=creds)
    video_id = upload_video(youtube, output_mp4, title, desc)
    
    if video_id:
        # Añadir a la Playlist correspondiente a la Serie
        playlist_id = get_or_create_playlist(youtube, serie)
        add_video_to_playlist(youtube, video_id, playlist_id)
        
        # 6. Marcar como DONE
        sheet.update_cell(row_idx, estado_col_idx, "DONE")
        print("¡Proceso Finalizado Exitosamente! Fila marcada como DONE.")
    else:
        print("Error en la subida, no se marcó como DONE.")

if __name__ == "__main__":
    main()
