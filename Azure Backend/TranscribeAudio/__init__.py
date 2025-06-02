import azure.functions as func
import os
import uuid
import tempfile
from azure.cognitiveservices.speech import SpeechConfig, AudioConfig, SpeechRecognizer, ResultReason

def transcribe_audio(file_path: str) -> str:
    speech_config = SpeechConfig(subscription=os.environ["AZURE_SPEECH_KEY"],
                                 region=os.environ["AZURE_SPEECH_REGION"])
    audio_config = AudioConfig(filename=file_path)
    recognizer = SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    result = recognizer.recognize_once()
    return result.text if result.reason == ResultReason.RecognizedSpeech else f"Failed: {result.reason}"

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Get the audio file
        file = req.files.get('file')
        if not file:
            return func.HttpResponse("No file uploaded", status_code=400)

        # Save file temporarily
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.wav")
        with open(file_path, "wb") as f:
            f.write(file.read())

        # Transcribe
        transcript = transcribe_audio(file_path)

        # Optional: Save transcript
        transcript_path = file_path.replace(".wav", ".txt")
        with open(transcript_path, "w") as f:
            f.write(transcript)

        return func.HttpResponse(transcript, status_code=200)

    except Exception as e:
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
