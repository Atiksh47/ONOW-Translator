import streamlit as st
from streamlit_mic_recorder import mic_recorder
from openai import OpenAI  # updated import for new SDK
from dotenv import load_dotenv
import os


st.title("A transcriber Bot that translate speech to english text with OpenAI Whisper")
st.header("Currently using Hindi as an example")
# Get OpenAI API key
load_dotenv("secret.env")  # Add this line before accessing env vars

openai_api_key = os.getenv("OPENAI_API_KEY")
# Create OpenAI client with API key
client = OpenAI(api_key=openai_api_key)

st.write("Click the microphone to record:")

audio = mic_recorder(
    start_prompt="🎤 Start recording",
    stop_prompt="⏹️ Stop recording",
    key="recorder"
)

if audio:
    st.audio(audio["bytes"])
    
    # Save audio to file
    with open("temp_audio.wav", "wb") as f:
        f.write(audio["bytes"])
    
    # Transcribe with Whisper using the new API style
    try:
        with open("temp_audio.wav", "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
                language="hi"
            )
            hindi_text = transcript.text
            st.write("Original Transcription (Hindi):")
            st.success(hindi_text)
            
            # Step 2: Translate to English using Chat Completion
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful translator."},
                    {"role": "user", "content": f"Translate this Hindi text to English:\n\n{hindi_text}"}
                ]
            )
            translation = response.choices[0].message.content
            st.write("Translated to English:")
            st.success(translation)
    except Exception as e:
        st.error(f"Error in transcription: {e}")