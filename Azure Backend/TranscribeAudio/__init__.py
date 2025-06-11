import azure.functions as func
import os
import uuid
import tempfile
import subprocess
import requests
import json
import time
import logging
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from azure.cognitiveservices.speech import SpeechConfig
from azure.cognitiveservices.speech.transcription import TranscriptionClient, TranscriptionProperties
from datetime import datetime, timedelta

def convert_mp4_to_wav(mp4_path: str, wav_path: str) -> None:
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

def save_transcript_to_blob(transcript_text: str, file_id: str) -> None:
    connect_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container_name = os.environ["AZURE_STORAGE_CONTAINER"]
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    blob_name = f"transcripts/{file_id}.txt"
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    blob_client.upload_blob(transcript_text, overwrite=True)

def transcribe_audio_batch(file_url: str) -> str:
    speech_config = SpeechConfig(
        subscription=os.environ["AZURE_SPEECH_KEY"],
        region=os.environ["AZURE_SPEECH_REGION"]
    )
    transcription_client = TranscriptionClient(speech_config)
    properties = TranscriptionProperties(language="en-US", diarization_enabled=True)
    transcription = transcription_client.create_transcription_from_url(file_url, properties=properties)

    while True:
        transcription = transcription_client.get_transcription(transcription.id)
        if transcription.status == "Succeeded":
            break
        elif transcription.status == "Failed":
            raise Exception("Transcription failed")
        time.sleep(5)

    results = requests.get(transcription.results_urls["channel_0"])
    transcription_result = results.json()
    transcription_client.delete_transcription(transcription.id)

    combined_text = " ".join([item["text"] for item in transcription_result["segments"]])
    return combined_text

def main(req: func.HttpRequest) -> func.HttpResponse:
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

        transcript = transcribe_audio_batch(blob_url)

        file_id = str(uuid.uuid4())
        save_transcript_to_blob(transcript, file_id)

        os.remove(mp4_path)
        os.remove(wav_path)

        return func.HttpResponse(f"Transcript saved successfully with ID: {file_id}", status_code=200)

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
