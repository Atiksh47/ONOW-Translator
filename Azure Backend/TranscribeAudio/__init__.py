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
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from azure.cognitiveservices.speech import SpeechConfig
from datetime import datetime, timedelta

def convert_mp4_to_wav(mp4_path: str, wav_path: str) -> None:
   ''' ffmpeg_path = os.path.join(os.path.dirname(__file__), '../ffmpeg/ffmpeg')
    os.chmod(ffmpeg_path, os.stat(ffmpeg_path).st_mode | stat.S_IEXEC)

    subprocess.run([
        ffmpeg_path, "-y", "-i", mp4_path,
        "-ar", "16000",  # 16kHz sample rate for STT
        "-ac", "1",      # mono channel
        wav_path
    ], check=True) '''
   
   subprocess.run([
        "ffmpeg", "-y", "-i", mp4_path,
        "-ar", "16000",  # 16kHz sample rate for STT
        "-ac", "1",      # mono channel
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

def translate_to_english(text: str) -> str:
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
        "to": "en"
    }
    
    body = [{"text": text}]
    
    response = requests.post(endpoint, headers=headers, params=params, json=body)
    if response.status_code != 200:
        raise Exception(f"Translation failed: {response.text}")
        
    translation_result = response.json()
    return translation_result[0]["translations"][0]["text"]

def create_transcription(file_url: str) -> str:
    """Creates a transcription job using Azure Speech REST API"""
    endpoint = f"https://{os.environ['AZURE_SPEECH_REGION']}.api.cognitive.microsoft.com/speechtotext/v3.0/transcriptions"
    headers = {
        "Ocp-Apim-Subscription-Key": os.environ["AZURE_SPEECH_KEY"],
        "Content-Type": "application/json"
    }
    
    body = {
        "displayName": f"Transcription for {file_url}",
        "contentUrls": [file_url],
        "properties": {
            "diarizationEnabled": True,
            "wordLevelTimestampsEnabled": True,
            "languageIdentification": {
                "candidateLocales": ["en-US", "hi-IN", "te-IN", "ta-IN", "mr-IN", "gu-IN", "kn-IN", "pa-IN", "bn-IN"],
            }
        },
        "locale": "en-US",
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

def transcribe_audio_batch(file_url: str) -> tuple[str, str]:
    """Handles the complete transcription process"""
    # Start transcription
    transcription_url = create_transcription(file_url)
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
            english_text = translate_to_english(combined_text) if combined_text else ""
            
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

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Function started")
    
    try:
        req_body = req.get_json()
        file_url = req_body.get("file_url")
        if not file_url:
            return func.HttpResponse("Missing 'file_url' field in JSON body", status_code=400)

        logging.info(f"Downloading file from {file_url}")
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

        original_text, english_text = transcribe_audio_batch(blob_url)

        file_id = str(uuid.uuid4())
        save_transcript_to_blob(original_text, english_text, file_id)

        os.remove(mp4_path)
        os.remove(wav_path)

        return func.HttpResponse(
            json.dumps({
                "file_id": file_id,
                "original_text": original_text,
                "english_text": english_text
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
