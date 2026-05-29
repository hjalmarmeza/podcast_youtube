import os
import sys
import json
import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from generar_videos import process_episode

# === CONFIGURACION ===
# NOTA: En GitHub Actions, estas variables vendrán del entorno. Localmente, puedes ponerlas aquí o en variables de entorno.
DEEPINFRA_API_KEY = os.environ.get("DEEPINFRA_API_KEY")
YOUTUBE_TOKEN_PATH = "token.json"
YOUTUBE_CREDS_PATH = "credentials.json"
SHEET_ID = "1lOrZJWQs6PjouAPvv4VHHQAUWPu3sPTLpUdyH2wLkFE"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "Audios de podcast")

def get_youtube_service():
    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None
    if os.path.exists(YOUTUBE_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(YOUTUBE_TOKEN_PATH, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(YOUTUBE_CREDS_PATH):
                raise Exception("Falta credentials.json de YouTube")
            flow = InstalledAppFlow.from_client_secrets_file(YOUTUBE_CREDS_PATH, scopes)
            creds = flow.run_local_server(port=0)
        with open(YOUTUBE_TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)

def get_sheet_data():
    # Asumimos que tenemos acceso público de lectura o credenciales de service account.
    # Como el usuario me pasó el link con "edit?usp=sharing", tal vez esté público.
    # Usaremos la API de gspread de forma anónima si es público, o requerirá credenciales.
    # Por ahora intentamos descargar el CSV directamente para ser más simples si no hay credenciales de service account.
    csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Hoja 2"
    import pandas as pd
    try:
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        print(f"Error leyendo el Sheet: {e}")
        return None

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
Tengo un episodio de podcast corto con esta información:
Serie: {serie}
Tema Central: {tema}
Pasaje Principal: {pasaje}
Enfoque: {enfoque}

Genera un Título SEO para YouTube (máximo 100 caracteres) y una Descripción atractiva (incluyendo llamados a la acción, el pasaje y hashtags). 
Devuelve el resultado en formato JSON con dos claves: "titulo" y "descripcion". No uses markdown extra, solo el JSON puro.
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
        print(f"Error generando metadatos con Deepinfra: {e}")
        return f"{tema} | {serie}", f"{enfoque}\n\nPasaje: {pasaje}\n#MusichrisStudio"

def upload_video(youtube, file_path, title, description, thumbnail_path=None):
    print(f"Subiendo a YouTube: {title}")
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "22" # People & Blogs
        },
        "status": {
            "privacyStatus": "private", # Se sube privado por seguridad
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
    
    if thumbnail_path and os.path.exists(thumbnail_path):
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path)
        ).execute()
        print("Miniatura actualizada.")
        
    return video_id

def main():
    print("Iniciando Motor de Subida Diaria...")
    # TODO: Implementar lógica de bucle sobre el dataframe para encontrar el primero sin procesar
    # Como requiere autenticación para ESCRIBIR en el Google Sheet (marcar como DONE),
    # será necesario configurar una Service Account o usar el mismo OAuth de YouTube si incluimos el scope de Drive/Sheets.
    # Para el script actual de prueba, está en pausa hasta definir la escritura.

if __name__ == "__main__":
    main()
