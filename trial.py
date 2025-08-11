# FIXED TIME DURATION RECORDING


# # import streamlit as st
# import pandas as pd
# import sounddevice as sd
# import queue
# import vosk
# import json
# import pyttsx3
# import requests

# # =========================
# # INITIAL SETUP
# # =========================
# # Initialize storage for survey results
# if 'survey_data' not in st.session_state:
#     st.session_state.survey_data = []

# # Load Vosk STT model (download beforehand: https://alphacephei.com/vosk/models)
# vosk_model = vosk.Model("/home/hiren/Desktop/SurveyBot/models/vosk-model-small-en-us-0.15")
# q = queue.Queue()

# # TTS initialization
# engine = pyttsx3.init()

# # Ollama API configuration (local LLM)
# OLLAMA_URL = "http://localhost:11434/api/generate"
# OLLAMA_MODEL = "mistral"  # Ensure you have run: ollama pull mistral

# # =========================
# # FUNCTIONS
# # =========================
# # Record audio from mic
# def record_audio(duration=6, fs=16000):
#     st.write("🎙 Recording...")
#     q.queue.clear()
#     recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
#     sd.wait()
#     return recording

# # Speech-to-text (offline, Vosk)
# def transcribe_audio(audio):
#     rec = vosk.KaldiRecognizer(vosk_model, 16000)
#     rec.AcceptWaveform(audio.tobytes())
#     result = json.loads(rec.FinalResult())
#     return result.get("text", "")

# # Ask local LLM (Ollama)
# def ask_llm(prompt):
#     payload = {
#         "model": OLLAMA_MODEL,
#         "prompt": prompt,
#         "stream": False
#     }
#     try:
#         response = requests.post(OLLAMA_URL, json=payload)
#         if response.status_code == 200:
#             return response.json().get("response", "")
#         else:
#             return f"Error from Ollama API: {response.status_code}"
#     except requests.exceptions.ConnectionError:
#         return "Error: Could not connect to Ollama. Is it running?"

# # Text-to-speech (offline, pyttsx3)
# def speak(text):
#     engine.say(text)
#     engine.runAndWait()

# # =========================
# # SURVEY LOGIC
# # =========================
# questions = [
#     "What is your name?",
#     "How satisfied are you with our services?",
#     "Any suggestions for improvement?"
# ]

# st.title("🎤 Offline Voice Survey Bot")

# if st.button("Start Survey"):
#     for qn in questions:
#         speak(qn)
#         st.write(f"🤖 Bot: {qn}")

#         # Record + transcribe user answer
#         audio = record_audio()
#         user_text = transcribe_audio(audio)
#         st.write(f"🗣 You: {user_text}")

#         # (Optional) Bot can respond conversationally using LLM
#         bot_reply = ask_llm(f"You are conducting a survey. User answered: '{user_text}'. Respond briefly.")
#         st.write(f"🤖 Bot: {bot_reply}")
#         speak(bot_reply)

#         # Save the Q&A
#         st.session_state.survey_data.append({"Question": qn, "Answer": user_text})

#     # Save all answers to CSV
#     df = pd.DataFrame(st.session_state.survey_data)
#     df.to_csv("survey_results.csv", index=False)
#     st.success("✅ Survey Completed! Answers saved to survey_results.csv")


# app.py
import os
import time
import datetime
import queue
import numpy as np
import pandas as pd
import streamlit as st
import sounddevice as sd
import webrtcvad
import soundfile as sf
import vosk
import json
import pyttsx3

# -------------------------
# CONFIG
# -------------------------
VOSK_MODEL_PATH = "/home/hiren/Desktop/SurveyBot/models/vosk-model-small-en-us-0.15"

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
# Initialize TTS
# -------------------------
engine = pyttsx3.init()

# -------------------------
# Load Vosk model
# -------------------------
try:
    vosk_model = vosk.Model(VOSK_MODEL_PATH)
except Exception as e:
    st.error(f"Could not load Vosk model at '{VOSK_MODEL_PATH}': {e}")
    st.stop()

# -------------------------
# Helpers
# -------------------------
def save_wav(filename: str, data: np.ndarray, samplerate: int = SAMPLE_RATE):
    sf.write(filename, data.astype(np.int16), samplerate, subtype='PCM_16')

def record_until_silence(sample_rate=SAMPLE_RATE,
                         frame_duration_ms=FRAME_DURATION_MS,
                         max_seconds=MAX_RECORD_SECONDS,
                         silence_window=SILENCE_WINDOW_SEC,
                         vad_aggressiveness=VAD_AGGRESSIVENESS):
    vad = webrtcvad.Vad(vad_aggressiveness)
    frame_size = int(sample_rate * (frame_duration_ms / 1000.0))
    recorded_frames = []
    frames_needed = max(1, int((silence_window * 1000) / frame_duration_ms))
    silence_ring = [False] * frames_needed
    stop_flag = {"stop": False}

    def callback(indata, frames, time_info, status):
        if status:
            print("Stream status:", status)
        mono = indata.mean(axis=1) if indata.ndim > 1 else indata
        int16_data = (mono * 32767).astype(np.int16) if mono.dtype != np.int16 else mono
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

def transcribe_with_vosk(int16_audio: np.ndarray, sample_rate=SAMPLE_RATE):
    if int16_audio.size == 0:
        return ""
    rec = vosk.KaldiRecognizer(vosk_model, sample_rate)
    chunk_size = 4000
    audio_bytes = int16_audio.tobytes()
    for i in range(0, len(audio_bytes), chunk_size):
        rec.AcceptWaveform(audio_bytes[i:i+chunk_size])
    try:
        return json.loads(rec.FinalResult()).get("text", "")
    except Exception:
        return ""

def speak_text(text: str):
    engine.say(text)
    engine.runAndWait()

# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title=" Voice Survey Bot", layout="centered")
st.title("🎤 Voice Survey Bot ")

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
    st.session_state.conversation_done = False
    for idx, qtext in enumerate(questions):
        # Bot asks
        st.write(f"🤖 Bot: {qtext}")
        speak_text(qtext)

        # User answers
        st.write("🔴 Listening...")
        audio_arr = record_until_silence()
        if audio_arr.size == 0:
            st.warning("No audio captured. Skipping this question.")
            continue

        # Save audio
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"answer_{idx+1}_{ts}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)
        save_wav(filepath, audio_arr, SAMPLE_RATE)

        # Transcribe
        st.write("⏳ Transcribing...")
        answer_text = transcribe_with_vosk(audio_arr, SAMPLE_RATE)
        st.write(f"🗣 You: {answer_text if answer_text else '[no transcription]'}")

        # Optional bot acknowledgement
        bot_reply = "Thanks for your answer."
        st.write(f"🤖 Bot: {bot_reply}")
        speak_text(bot_reply)

        # Save to CSV
        row = {
            "timestamp": datetime.datetime.now().isoformat(),
            "question": qtext,
            "answer_text": answer_text,
            #"audio_filename": filepath
        }
        pd.DataFrame([row]).to_csv(CSV_FILE, mode='a', header=False, index=False)

    st.session_state.conversation_done = True
    st.success("✅ Conversation completed and saved.")

if st.session_state.conversation_done:
    st.subheader("Survey Results")
    st.dataframe(pd.read_csv(CSV_FILE))
