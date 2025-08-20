# full - working with elevenlabs 
import os
import time
import datetime
import io
import numpy as np
import pandas as pd
import streamlit as st
import sounddevice as sd
import soundfile as sf
import requests
import webrtcvad
from elevenlabs import ElevenLabs
from dotenv import load_dotenv

# -------------------------
# LOAD ENV VARIABLES
# -------------------------
load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")       # Your Deepgram API key
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")   # Your ElevenLabs API key
BOT_VOICE_ID = os.getenv("BOT_VOICE_ID", "replace_with_your_voice_id")

if not DEEPGRAM_API_KEY or not ELEVENLABS_API_KEY:
    st.error("Missing API keys. Please set DEEPGRAM_API_KEY and ELEVENLABS_API_KEY in your .env file.")
    st.stop()

# Init ElevenLabs client
client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# -------------------------
# CONFIG
# -------------------------
DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"
OUTPUT_DIR = "survey_outputs"
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
CSV_FILE = os.path.join(OUTPUT_DIR, "survey_results.csv")

SAMPLE_RATE = 16000
CHANNELS = 1
FRAME_DURATION_MS = 30
MAX_RECORD_SECONDS = 30
SILENCE_WINDOW_SEC = 1.2
VAD_AGGRESSIVENESS = 1

# -------------------------
# Setup folders
# -------------------------
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -------------------------
# Utility: List voices
# -------------------------
def list_voices():
    """Print all available ElevenLabs voices (voice_id and name)"""
    voices = client.voices.get_all().voices
    for v in voices:
        print(f"{v.voice_id} - {v.name}")
    return voices

# -------------------------
# Audio Helpers
# -------------------------
def save_wav(filename: str, data: np.ndarray, samplerate: int = SAMPLE_RATE):
    """Save int16 numpy array as PCM16 wav"""
    sf.write(filename, data.astype(np.int16), samplerate, subtype='PCM_16')

def record_until_silence(sample_rate=SAMPLE_RATE,
                         frame_duration_ms=FRAME_DURATION_MS,
                         max_seconds=MAX_RECORD_SECONDS,
                         silence_window=SILENCE_WINDOW_SEC,
                         vad_aggressiveness=VAD_AGGRESSIVENESS):
    """Record until user stops speaking for given silence window."""
    vad = webrtcvad.Vad(vad_aggressiveness)
    frame_size = int(sample_rate * (frame_duration_ms / 1000.0))
    recorded_frames = []
    frames_needed = max(1, int((silence_window * 1000) / frame_duration_ms))
    silence_ring = [True] * frames_needed
    stop_flag = {"stop": False}

    def callback(indata, frames, time_info, status):
        mono = indata.mean(axis=1) if indata.ndim > 1 else indata
        int16_data = (mono * 32767).astype(np.int16)
        recorded_frames.append(int16_data.copy())
        try:
            is_speech = vad.is_speech(int16_data.tobytes(), sample_rate)
        except Exception:
            is_speech = True
        silence_ring.pop(0)
        silence_ring.append(is_speech)
        if not any(silence_ring) and len(recorded_frames) > frames_needed:
            stop_flag["stop"] = True

    with sd.InputStream(samplerate=sample_rate, channels=CHANNELS, dtype='float32',
                        blocksize=frame_size, callback=callback):
        start_time = time.time()
        while True:
            time.sleep(0.01)
            if stop_flag["stop"]:
                break
            if time.time() - start_time > max_seconds:
                break

    if not recorded_frames:
        return np.zeros(0, dtype=np.int16)

    audio = np.concatenate(recorded_frames, axis=0)
    if audio.dtype != np.int16:
        audio = (audio * 32767).astype(np.int16)
    return audio

# -------------------------
# Deepgram STT
# -------------------------
def transcribe_with_deepgram(int16_audio: np.ndarray, sample_rate=SAMPLE_RATE):
    """Send recorded audio to Deepgram and return transcript."""
    if int16_audio.size == 0:
        return ""
    wav_path = "temp_audio.wav"
    save_wav(wav_path, int16_audio, sample_rate)

    with open(wav_path, "rb") as f:
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "audio/wav"
        }
        params = {"punctuate": "true", "model": "nova-2"}
        try:
            response = requests.post(DEEPGRAM_URL, headers=headers, params=params, data=f, timeout=30)
        except Exception as e:
            return f"[Deepgram request error: {e}]"

    if response.status_code == 200:
        try:
            result = response.json()
            return result["results"]["channels"][0]["alternatives"][0]["transcript"]
        except Exception as e:
            return f"[Parsing error: {e}]"
    else:
        return f"[Deepgram error: {response.status_code} {response.text}]"

# -------------------------
# ElevenLabs TTS (latest SDK, streaming fix)
# -------------------------
def speak_text(text: str, voice_id: str):
    """
    Convert text to speech using ElevenLabs and play locally (blocking).
    voice_id must be a valid ElevenLabs voice ID from your account.
    """
    try:
        # Streamed audio generator from ElevenLabs
        audio_stream = client.text_to_speech.convert(
            voice_id=voice_id,
            model_id="eleven_monolingual_v1",
            text=text
        )

        # Merge all streamed chunks into one bytes object
        audio_bytes = b"".join(audio_stream)

        # Play the audio
        data, samplerate = sf.read(io.BytesIO(audio_bytes), dtype='float32')
        sd.play(data, samplerate)
        sd.wait()

    except Exception as e:
        st.error(f"TTS error: {e}")
        print("TTS error:", e)

# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title="Voice Survey Bot", layout="centered")
st.title("🎤 Voice Survey Bot (Deepgram + ElevenLabs)")

questions = [
    "Hello, what is your name?",
    "How satisfied are you with our services, on a scale of 1 to 5?",
    "Any suggestions for improvement?",
    "Thank you — that completes the survey."
]

if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=["timestamp", "question", "answer_text", "audio_filename"]).to_csv(CSV_FILE, index=False)

if "conversation_done" not in st.session_state:
    st.session_state.conversation_done = False

if st.button("▶ Start Conversation"):
    if BOT_VOICE_ID.startswith("replace"):
        st.error("Please set BOT_VOICE_ID in your .env file or script.")
        st.stop()

    st.session_state.conversation_done = False
    for idx, qtext in enumerate(questions):
        st.write(f"🤖 Bot: {qtext}")
        speak_text(qtext, voice_id=BOT_VOICE_ID)

        st.write("🔴 Listening...")
        audio_arr = record_until_silence()
        if audio_arr.size == 0:
            st.warning("No audio captured. Skipping this question.")
            continue

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"answer_{idx+1}_{ts}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)
        save_wav(filepath, audio_arr, SAMPLE_RATE)

        st.write("⏳ Transcribing...")
        answer_text = transcribe_with_deepgram(audio_arr, SAMPLE_RATE)
        st.write(f"🗣 You: {answer_text if answer_text else '[no transcription]'}")

        bot_reply = "Thanks for your answer."
        st.write(f"🤖 Bot: {bot_reply}")
        speak_text(bot_reply, voice_id=BOT_VOICE_ID)

        row = {
            "timestamp": datetime.datetime.now().isoformat(),
            "question": qtext,
            "answer_text": answer_text,
            "audio_filename": filepath
        }
        pd.DataFrame([row]).to_csv(CSV_FILE, mode='a', header=False, index=False)

    st.session_state.conversation_done = True
    st.success("✅ Conversation completed and saved.")

if st.session_state.conversation_done:
    st.subheader("Survey Results")
    st.dataframe(pd.read_csv(CSV_FILE))
