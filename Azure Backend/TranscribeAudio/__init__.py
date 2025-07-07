import azure.functions as func
import os
import uuid
import tempfile
import subprocess
import requests
import json
import time
import stat
import logging
import zipfile
import io
import tarfile
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from azure.cognitiveservices.speech import SpeechConfig
from datetime import datetime, timedelta
from .language_config import get_language_config, get_supported_countries

#local Testing
"""
def convert_mp4_to_wav(mp4_path: str, wav_path: str) -> None:
   ffmpeg_path = os.path.join(os.path.dirname(__file__), 'ffmpeg', 'ffmpeg')
   
   subprocess.run([
        ffmpeg_path, "-y", "-i", mp4_path,
        "-ar", "16000",  # 16kHz sample rate for STT
        "-ac", "1",      # mono channel
        wav_path
    ], check=True)
   
   '''subprocess.run([
        "ffmpeg", "-y", "-i", mp4_path,
        "-ar", "16000",  # 16kHz sample rate for STT
        "-ac", "1",      # mono channel
        wav_path
    ], check=True) '''
    
"""
#Azure Testing
def get_tmp_ffmpeg_path() -> str:
    tmp_ffmpeg_path = "/tmp/ffmpeg"
    if not os.path.exists(tmp_ffmpeg_path):
        print("Downloading ffmpeg static Linux build...")
        ffmpeg_url = "https://www.johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        archive_path = "/tmp/ffmpeg.tar.xz"

        # Download .tar.xz archive
        with requests.get(ffmpeg_url, stream=True) as r:
            r.raise_for_status()
            with open(archive_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        # Extract archive
        with tarfile.open(archive_path, mode='r:xz') as tar:
            for member in tar.getmembers():
                if member.isfile() and os.path.basename(member.name) == "ffmpeg":
                    member.name = os.path.basename(member.name)  # Remove path
                    tar.extract(member, path="/tmp")
                    break

        os.rename("/tmp/ffmpeg", tmp_ffmpeg_path)
        os.chmod(tmp_ffmpeg_path, os.stat(tmp_ffmpeg_path).st_mode | stat.S_IEXEC)

    return tmp_ffmpeg_path

def convert_mp4_to_wav(mp4_path: str, wav_path: str) -> None:
    ffmpeg_path = get_tmp_ffmpeg_path()
    subprocess.run([
        ffmpeg_path,
        "-y", "-i", mp4_path,
        "-ar", "16000",
        "-ac", "1",
        wav_path
    ], check=True)

def upload_to_blob(file_path: str) -> str:
    connect_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container_name = os.environ["AZURE_STORAGE_CONTAINER"]
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    blob_name = f"audio/{uuid.uuid4()}{os.path.splitext(file_path)[1]}"
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    with open(file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

    sas_token = generate_blob_sas(
        account_name=blob_service_client.account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=blob_service_client.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=1)
    )

    return f"{blob_client.url}?{sas_token}"

def translate_to_english(text: str, country: str) -> str:
    """
    Translate text to English based on the source country/language.
    
    Args:
        text: Text to translate
        country: Source country (required)
        
    Returns:
        Translated English text
    """
    lang_config = get_language_config(country)
    
    translator_key = os.environ["AZURE_TRANSLATOR_KEY"]
    translator_region = os.environ["AZURE_TRANSLATOR_REGION"]
    endpoint = "https://api.cognitive.microsofttranslator.com/translate"
    
    headers = {
        "Ocp-Apim-Subscription-Key": translator_key,
        "Ocp-Apim-Subscription-Region": translator_region,
        "Content-Type": "application/json"
    }
    
    params = {
        "api-version": "3.0",
        "from": lang_config.translate_from,
        "to": lang_config.translate_to
    }
    
    body = [{"text": text}]
    
    response = requests.post(endpoint, headers=headers, params=params, json=body)
    if response.status_code != 200:
        raise Exception(f"Translation failed: {response.text}")
        
    translation_result = response.json()
    return translation_result[0]["translations"][0]["text"]

def create_transcription(file_url: str, country: str) -> str:
    """
    Creates a transcription job using Azure Speech REST API
    
    Args:
        file_url: URL of the audio file to transcribe
        country: Source country for language detection (required)
    """
    lang_config = get_language_config(country)
    
    endpoint = f"https://{os.environ['AZURE_SPEECH_REGION']}.api.cognitive.microsoft.com/speechtotext/v3.0/transcriptions"
    headers = {
        "Ocp-Apim-Subscription-Key": os.environ["AZURE_SPEECH_KEY"],
        "Content-Type": "application/json"
    }
    
    body = {
        "displayName": f"Transcription for {file_url}",
        "contentUrls": [file_url],
        "locale": lang_config.speech_locale,
        "properties": {
            "diarizationEnabled": True,
            "wordLevelTimestampsEnabled": True,
        },
    }
    
    response = requests.post(endpoint, headers=headers, json=body)
    if response.status_code != 201:
        raise Exception(f"Failed to create transcription: {response.text}")
    
    return response.json()["self"]

def get_transcription_status(transcription_url: str) -> dict:
    """Gets the status of a transcription job"""
    headers = {
        "Ocp-Apim-Subscription-Key": os.environ["AZURE_SPEECH_KEY"]
    }
    
    response = requests.get(transcription_url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to get transcription status: {response.text}")
    
    return response.json()

def get_transcription_result(files_url: str) -> str:
    """Gets the final transcription result"""
    headers = {
        "Ocp-Apim-Subscription-Key": os.environ["AZURE_SPEECH_KEY"]
    }
    
    # Get the files list
    response = requests.get(files_url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to get files list: {response.text}")
    
    # Get the transcription file URL
    files = response.json()["values"]
    if not files:
        raise Exception("No transcription files found")
    
    # Get the actual transcription
    response = requests.get(files[0]["links"]["contentUrl"], headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to get transcription content: {response.text}")
    
    return response.json()

def transcribe_audio_batch(file_url: str, country: str) -> tuple[str, str]:
    """
    Handles the complete transcription process
    
    Args:
        file_url: URL of the audio file to transcribe
        country: Source country for language detection (required)
    """
    # Start transcription
    transcription_url = create_transcription(file_url, country)
    logging.info(f"Created transcription job: {transcription_url}")
    
    # Poll for completion
    while True:
        status = get_transcription_status(transcription_url)
        logging.info(f"Transcription status: {status['status']}")
        
        if status["status"] == "Succeeded":
            # Get results
            result = get_transcription_result(status["links"]["files"])
            
            # Combine all recognized phrases
            combined_text = " ".join([item["nBest"][0]["display"] for item in result["recognizedPhrases"]])
            
            # Delete the transcription
            requests.delete(transcription_url, headers={
                "Ocp-Apim-Subscription-Key": os.environ["AZURE_SPEECH_KEY"]
            })
            
            # Translate to English if needed
            english_text = translate_to_english(combined_text, country) if combined_text else ""
            
            return combined_text, english_text
            
        elif status["status"] == "Failed":
            raise Exception(f"Transcription failed: {status.get('statusMessage', 'Unknown error')}")
            
        time.sleep(5)

def save_transcript_to_blob(original_text: str, english_text: str, file_id: str) -> None:
    connect_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container_name = os.environ["AZURE_STORAGE_CONTAINER"]
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    
    # Save original transcript
    original_blob_name = f"transcripts/{file_id}_original.txt"
    original_blob_client = blob_service_client.get_blob_client(container=container_name, blob=original_blob_name)
    original_blob_client.upload_blob(original_text, overwrite=True)
    
    # Save English translation
    english_blob_name = f"transcripts/{file_id}_english.txt"
    english_blob_client = blob_service_client.get_blob_client(container=container_name, blob=english_blob_name)
    english_blob_client.upload_blob(english_text, overwrite=True)

def generate_transcript_blob_link(file_id: str, language: str = "english") -> str:
    connect_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container_name = os.environ["AZURE_STORAGE_CONTAINER"]
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)

    # Map language parameter to actual blob naming convention
    if language.lower() == "original":
        blob_name = f"transcripts/{file_id}_original.txt"
    elif language.lower() == "english":
        blob_name = f"transcripts/{file_id}_english.txt"
    else:
        raise ValueError(f"Unsupported language: {language}. Use 'original' or 'english'")

    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    sas_token = generate_blob_sas(
        account_name=blob_service_client.account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=blob_service_client.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=24)
    )

    return f"{blob_client.url}?{sas_token}"


def send_to_bubble(file_id: str, blob_url: str, max_retries: int = 3, retry_delay: float = 1.0):
    """
    Send transcript blob URL to Bubble webhook with retry logic
    
    Args:
        file_id: Unique identifier for the file
        blob_url: The blob storage URL with SAS token for the transcript
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
    """
    bubble_endpoint = os.environ.get("BUBBLE_WEBHOOK_URL")
    
    if not bubble_endpoint:
        logging.error("BUBBLE_WEBHOOK_URL environment variable not set")
        return False

    payload = {
        "file_id": file_id,
        "transcript_url": blob_url,
        "timestamp": datetime.utcnow().isoformat()
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "ONOW-Translator/1.0"
    }

    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                bubble_endpoint, 
                json=payload, 
                headers=headers,
                timeout=30  # 30 second timeout
            )
            
            if response.status_code in [200, 201]:
                logging.info(f"Successfully sent transcript URL to Bubble (attempt {attempt + 1}): {response.text}")
                return True
            else:
                logging.warning(f"Bubble webhook returned status {response.status_code} (attempt {attempt + 1}): {response.text}")
                
        except requests.exceptions.RequestException as e:
            logging.warning(f"Request failed (attempt {attempt + 1}): {str(e)}")
        
        # Don't sleep on the last attempt
        if attempt < max_retries:
            time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
    
    logging.error(f"Failed to send transcript URL to Bubble after {max_retries + 1} attempts")
    return False


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Function started")
    
    try:
        req_body = req.get_json()
        file_url = req_body.get("file_url")
        country = req_body.get("country")
        
        # Validate required parameters
        if not file_url:
            return func.HttpResponse(
                json.dumps({
                    "error": "Missing 'file_url' field in JSON body",
                    "supported_countries": get_supported_countries()
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        if not country:
            return func.HttpResponse(
                json.dumps({
                    "error": "Missing 'country' field in JSON body",
                    "supported_countries": get_supported_countries()
                }),
                status_code=400,
                mimetype="application/json"
            )

        # Validate country is supported
        try:
            lang_config = get_language_config(country)
            logging.info(f"Processing audio from {file_url} for country: {country} ({lang_config.language_name})")
        except ValueError as e:
            return func.HttpResponse(
                json.dumps({
                    "error": str(e),
                    "supported_countries": get_supported_countries()
                }),
                status_code=400,
                mimetype="application/json"
            )

        response = requests.get(file_url)
        if response.status_code != 200:
            return func.HttpResponse("Failed to download file", status_code=400)

        temp_dir = tempfile.gettempdir()
        mp4_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp4")
        wav_path = mp4_path.rsplit('.', 1)[0] + '.wav'

        with open(mp4_path, "wb") as f:
            f.write(response.content)

        convert_mp4_to_wav(mp4_path, wav_path)

        blob_url = upload_to_blob(wav_path)

        original_text, english_text = transcribe_audio_batch(blob_url, country)

        file_id = str(uuid.uuid4())
        save_transcript_to_blob(original_text, english_text, file_id)

        #Level 2: Bubble Integration        
        transcript_url = generate_transcript_blob_link(file_id, language="english")
        send_to_bubble(file_id, transcript_url)


        os.remove(mp4_path)
        os.remove(wav_path)

        return func.HttpResponse(
            json.dumps({
                "file_id": file_id,
                "original_text": original_text,
                "english_text": english_text,
                "country": country,
                "language": lang_config.language_name,
                "supported_countries": get_supported_countries()
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "error": str(e),
                "supported_countries": get_supported_countries()
            }),
            status_code=500,
            mimetype="application/json"
        )
