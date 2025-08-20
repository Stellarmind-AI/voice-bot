# import os
# import io
# import uuid
# import datetime
# import pandas as pd
# from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
# from dotenv import load_dotenv
# from elevenlabs import ElevenLabs
# import requests

# # Load environment variables from .env when running locally
# load_dotenv()

# # Config / API keys
# DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
# ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
# BOT_VOICE_ID = os.getenv("BOT_VOICE_ID", "replace_with_your_voice_id")

# if not DEEPGRAM_API_KEY or not ELEVENLABS_API_KEY or BOT_VOICE_ID.startswith("replace_with_your_voice_id"):
#     raise RuntimeError("Please set DEEPGRAM_API_KEY, ELEVENLABS_API_KEY, BOT_VOICE_ID in .env")

# # Init clients
# tts_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
# DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"

# # App setup
# app = Flask(__name__, static_folder="static", template_folder="templates")
# OUTPUT_DIR = "survey_outputs"
# AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
# os.makedirs(AUDIO_DIR, exist_ok=True)
# os.makedirs(OUTPUT_DIR, exist_ok=True)

# CSV_FILE = os.path.join(OUTPUT_DIR, "survey_results.csv")
# if not os.path.exists(CSV_FILE):
#     pd.DataFrame(columns=["timestamp", "question_index", "question", "answer_text", "user_audio_path"]).to_csv(CSV_FILE, index=False)

# QUESTIONS = [
#     "Hello, what is your name?",
#     "How satisfied are you with our services, on a scale of 1 to 5?",
#     "Any suggestions for improvement?",
#     "Thank you — that completes the survey."
# ]

# def save_tts_wav(text: str) -> str:
#     """
#     Generate ElevenLabs TTS for `text`, save to static/audio, return a public URL path.
#     """
#     audio_stream = tts_client.text_to_speech.convert(
#         voice_id=BOT_VOICE_ID,
#         model_id="eleven_monolingual_v1",
#         text=text
#     )
#     audio_bytes = b"".join(audio_stream)
#     fname = f"{uuid.uuid4().hex}.wav"
#     fpath = os.path.join("static", "audio", fname)
#     os.makedirs(os.path.dirname(fpath), exist_ok=True)
#     with open(fpath, "wb") as f:
#         f.write(audio_bytes)
#     # Return path relative to site root
#     return f"/static/audio/{fname}"

# def deepgram_transcribe(raw_bytes: bytes, content_type: str) -> str:
#     """
#     Send audio bytes (webm/wav) to Deepgram synchronous endpoint and return transcript.
#     """
#     headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": content_type}
#     params = {"punctuate": "true", "model": "nova-2"}
#     try:
#         resp = requests.post(DEEPGRAM_URL, headers=headers, params=params, data=raw_bytes, timeout=40)
#     except Exception as e:
#         return f"[Deepgram request error: {e}]"

#     if resp.status_code == 200:
#         try:
#             j = resp.json()
#             return j["results"]["channels"][0]["alternatives"][0]["transcript"]
#         except Exception as e:
#             return f"[Parsing error: {e}]"
#     else:
#         return f"[Deepgram error: {resp.status_code} {resp.text}]"

# @app.route("/")
# def index():
#     return render_template("index.html")

# @app.route("/api/start", methods=["POST"])
# def api_start():
#     """
#     Return the first question TTS url and question text.
#     """
#     q_index = 0
#     question = QUESTIONS[q_index]
#     tts_url = save_tts_wav(question)
#     return jsonify({
#         "question_index": q_index,
#         "question_text": question,
#         "question_tts_url": tts_url,
#         "done": False
#     })

# @app.route("/api/answer", methods=["POST"])
# def api_answer():
#     """
#     Receive user audio (Blob) + question_index.
#     Save user's audio, transcribe via Deepgram, save CSV row.
#     Return ack TTS and next question TTS (or done).
#     """
#     q_index = int(request.form.get("question_index", "0"))
#     file = request.files.get("audio")
#     if not file:
#         return jsonify({"error": "No audio provided"}), 400

#     # Save user audio
#     user_audio_fname = f"user_{q_index+1}_{uuid.uuid4().hex}.webm"
#     user_audio_path = os.path.join(AUDIO_DIR, user_audio_fname)
#     os.makedirs(os.path.dirname(user_audio_path), exist_ok=True)
#     file.save(user_audio_path)

#     # Transcribe
#     content_type = file.content_type or "audio/webm"
#     file.stream.seek(0)
#     raw_bytes = file.read()
#     transcript = deepgram_transcribe(raw_bytes, content_type=content_type)

#     # Log to CSV
#     row = {
#         "timestamp": datetime.datetime.now().isoformat(),
#         "question_index": q_index,
#         "question": QUESTIONS[q_index] if q_index < len(QUESTIONS) else "",
#         "answer_text": transcript,
#         "user_audio_path": user_audio_path
#     }
#     pd.DataFrame([row]).to_csv(CSV_FILE, mode="a", header=False, index=False)

#     # Acknowledge + next
#     ack_text = "Thanks for your answer."
#     ack_tts_url = save_tts_wav(ack_text)

#     next_index = q_index + 1
#     if next_index < len(QUESTIONS):
#         next_q = QUESTIONS[next_index]
#         next_q_tts_url = save_tts_wav(next_q)
#         return jsonify({
#             "transcript": transcript,
#             "ack_text": ack_text,
#             "ack_tts_url": ack_tts_url,
#             "next_question_index": next_index,
#             "next_question_text": next_q,
#             "next_question_tts_url": next_q_tts_url,
#             "done": False
#         })
#     else:
#         done_text = "Thank you, the survey is complete."
#         done_tts_url = save_tts_wav(done_text)
#         return jsonify({
#             "transcript": transcript,
#             "ack_text": ack_text,
#             "ack_tts_url": ack_tts_url,
#             "done_text": done_text,
#             "done_tts_url": done_tts_url,
#             "done": True
#         })

# @app.route("/results", methods=["GET"])
# def results():
#     """
#     Serve the CSV results so users can view/download it.
#     """
#     if os.path.exists(CSV_FILE):
#         return send_file(CSV_FILE, mimetype="text/csv", as_attachment=False, download_name=os.path.basename(CSV_FILE))
#     else:
#         return "No results yet.", 404

# # Serve static audio files (Flask already does this for /static/* by default
# # but explicit route is OK if needed)
# @app.route("/static/audio/<path:filename>")
# def static_audio(filename):
#     return send_from_directory(os.path.join(app.root_path, "static", "audio"), filename)

# if __name__ == "__main__":
#     # For production use gunicorn instead of this dev server.
#     app.run(host="0.0.0.0", port=8000, debug=True)

# import os
# import io
# import uuid
# import datetime
# import pandas as pd
# from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
# from dotenv import load_dotenv
# from gtts import gTTS
# import requests

# # Load environment variables from .env when running locally
# load_dotenv()

# # Config / API keys
# DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# if not DEEPGRAM_API_KEY:
#     raise RuntimeError("Please set DEEPGRAM_API_KEY in .env")

# # App setup
# app = Flask(__name__, static_folder="static", template_folder="templates")

# OUTPUT_DIR = "survey_outputs"
# AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")

# os.makedirs(AUDIO_DIR, exist_ok=True)
# os.makedirs(OUTPUT_DIR, exist_ok=True)

# CSV_FILE = os.path.join(OUTPUT_DIR, "survey_results.csv")

# if not os.path.exists(CSV_FILE):
#     pd.DataFrame(columns=["timestamp", "question_index", "question", "answer_text", "user_audio_path"]).to_csv(CSV_FILE, index=False)

# QUESTIONS = [
#     "Hello, what is your name?",
#     "How satisfied are you with our services, on a scale of 1 to 5?",
#     "Any suggestions for improvement?",
#     "Thank you — that completes the survey."
# ]

# def save_tts_wav(text: str) -> str:
#     """
#     Generate gTTS TTS for `text`, save to static/audio as mp3, return a public URL path.
#     """
#     tts = gTTS(text=text, lang='en')
#     fname = f"{uuid.uuid4().hex}.mp3"
#     fpath = os.path.join("static", "audio", fname)
#     os.makedirs(os.path.dirname(fpath), exist_ok=True)
#     tts.save(fpath)
#     return f"/static/audio/{fname}"

# DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"

# def deepgram_transcribe(raw_bytes: bytes, content_type: str) -> str:
#     """
#     Send audio bytes (webm/wav) to Deepgram synchronous endpoint and return transcript.
#     """
#     headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": content_type}
#     params = {"punctuate": "true", "model": "nova-2"}

#     try:
#         resp = requests.post(DEEPGRAM_URL, headers=headers, params=params, data=raw_bytes, timeout=40)
#     except Exception as e:
#         return f"[Deepgram request error: {e}]"

#     if resp.status_code == 200:
#         try:
#             j = resp.json()
#             results = j.get("results")
#             if results:
#                 channels = results.get("channels")
#                 if isinstance(channels, list) and len(channels) > 0:
#                     alternatives = channels[0].get("alternatives")
#                     if isinstance(alternatives, list) and len(alternatives) > 0:
#                         transcript = alternatives.get("transcript", "")
#                         return transcript
#             return "[Transcript not found]"
#         except Exception as e:
#             return f"[Parsing error: {e}]"
#     else:
#         return f"[Deepgram error: {resp.status_code} {resp.text}]"

# @app.route("/")
# def index():
#     return render_template("index.html")

# @app.route("/api/start", methods=["POST"])
# def api_start():
#     q_index = 0
#     question = QUESTIONS[q_index]
#     tts_url = save_tts_wav(question)
#     return jsonify({
#         "question_index": q_index,
#         "question_text": question,
#         "question_tts_url": tts_url,
#         "done": False
#     })

# @app.route("/api/answer", methods=["POST"])
# def api_answer():
#     q_index = int(request.form.get("question_index", "0"))
#     file = request.files.get("audio")

#     if not file:
#         return jsonify({"error": "No audio provided"}), 400

#     user_audio_fname = f"user_{q_index+1}_{uuid.uuid4().hex}.webm"
#     user_audio_path = os.path.join(AUDIO_DIR, user_audio_fname)
#     os.makedirs(os.path.dirname(user_audio_path), exist_ok=True)
#     file.save(user_audio_path)

#     content_type = file.content_type or "audio/webm"
#     file.stream.seek(0)
#     raw_bytes = file.read()
#     transcript = deepgram_transcribe(raw_bytes, content_type=content_type)

#     row = {
#         "timestamp": datetime.datetime.now().isoformat(),
#         "question_index": q_index,
#         "question": QUESTIONS[q_index] if q_index < len(QUESTIONS) else "",
#         "answer_text": transcript,
#         "user_audio_path": user_audio_path
#     }
#     pd.DataFrame([row]).to_csv(CSV_FILE, mode="a", header=False, index=False)

#     ack_text = "Thanks for your answer."
#     ack_tts_url = save_tts_wav(ack_text)
#     next_index = q_index + 1

#     if next_index < len(QUESTIONS):
#         next_q = QUESTIONS[next_index]
#         next_q_tts_url = save_tts_wav(next_q)
#         return jsonify({
#             "transcript": transcript,
#             "ack_text": ack_text,
#             "ack_tts_url": ack_tts_url,
#             "next_question_index": next_index,
#             "next_question_text": next_q,
#             "next_question_tts_url": next_q_tts_url,
#             "done": False
#         })
#     else:
#         done_text = "Thank you, the survey is complete."
#         done_tts_url = save_tts_wav(done_text)
#         return jsonify({
#             "transcript": transcript,
#             "ack_text": ack_text,
#             "ack_tts_url": ack_tts_url,
#             "done_text": done_text,
#             "done_tts_url": done_tts_url,
#             "done": True
#         })

# @app.route("/results", methods=["GET"])
# def results():
#     if os.path.exists(CSV_FILE):
#         return send_file(CSV_FILE, mimetype="text/csv", as_attachment=False, download_name=os.path.basename(CSV_FILE))
#     else:
#         return "No results yet.", 404

# @app.route("/static/audio/<filename>")
# def static_audio(filename):
#     return send_from_directory(os.path.join(app.root_path, "static", "audio"), filename)

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=8000, debug=True)



import os
import uuid
import datetime
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
from dotenv import load_dotenv
from gtts import gTTS
import requests

# Load environment variables
load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

if not DEEPGRAM_API_KEY:
    raise RuntimeError("Please set DEEPGRAM_API_KEY in .env")

# Flask app setup
app = Flask(__name__, static_folder="static", template_folder="templates")

OUTPUT_DIR = "survey_outputs"
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

CSV_FILE = os.path.join(OUTPUT_DIR, "survey_results.csv")
if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=["timestamp", "question_index", "question", "answer_text", "user_audio_path"]).to_csv(CSV_FILE, index=False)

QUESTIONS = [
    "Hello, what is your name?",
    "How satisfied are you with our services, on a scale of 1 to 5?",
    "Any suggestions for improvement?",
    "Thank you — that completes the survey."
]

def save_tts_wav(text: str) -> str:
    """Generate gTTS TTS for text and save as mp3"""
    tts = gTTS(text=text, lang='en')
    fname = f"{uuid.uuid4().hex}.mp3"
    fpath = os.path.join("static", "audio", fname)
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    tts.save(fpath)
    return f"/static/audio/{fname}"

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"

def deepgram_transcribe(raw_bytes: bytes, content_type: str) -> str:
    """Send audio to Deepgram API and return transcript"""
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": content_type}
    params = {"punctuate": "true", "model": "nova-2"}

    try:
        resp = requests.post(DEEPGRAM_URL, headers=headers, params=params, data=raw_bytes, timeout=40)
    except Exception as e:
        return f"[Deepgram request error: {e}]"

    if resp.status_code == 200:
        try:
            j = resp.json()
            # Navigate safely
            results = j.get("results", {})
            channels = results.get("channels", [])
            if channels and "alternatives" in channels[0]:
                alternatives = channels[0]["alternatives"]
                if isinstance(alternatives, list) and len(alternatives) > 0:
                    transcript = alternatives[0].get("transcript", "")
                    return transcript if transcript else "[Empty transcript]"
            return "[Transcript not found]"
        except Exception as e:
            return f"[Parsing error: {e}]"
    else:
        return f"[Deepgram error: {resp.status_code} {resp.text}]"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/start", methods=["POST"])
def api_start():
    q_index = 0
    question = QUESTIONS[q_index]
    tts_url = save_tts_wav(question)
    return jsonify({
        "question_index": q_index,
        "question_text": question,
        "question_tts_url": tts_url,
        "done": False
    })

@app.route("/api/answer", methods=["POST"])
def api_answer():
    q_index = int(request.form.get("question_index", "0"))
    file = request.files.get("audio")

    if not file:
        return jsonify({"error": "No audio provided"}), 400

    # Save user audio
    user_audio_fname = f"user_{q_index+1}_{uuid.uuid4().hex}.webm"
    user_audio_path = os.path.join(AUDIO_DIR, user_audio_fname)
    os.makedirs(os.path.dirname(user_audio_path), exist_ok=True)
    file.save(user_audio_path)

    # Transcribe
    content_type = file.content_type or "audio/webm"
    file.stream.seek(0)
    raw_bytes = file.read()
    transcript = deepgram_transcribe(raw_bytes, content_type=content_type)

    # Save to CSV
    row = {
        "timestamp": datetime.datetime.now().isoformat(),
        "question_index": q_index,
        "question": QUESTIONS[q_index] if q_index < len(QUESTIONS) else "",
        "answer_text": transcript,
        "user_audio_path": user_audio_path
    }
    pd.DataFrame([row]).to_csv(CSV_FILE, mode="a", header=False, index=False)

    ack_text = "Thanks for your answer."
    ack_tts_url = save_tts_wav(ack_text)
    next_index = q_index + 1

    if next_index < len(QUESTIONS):
        next_q = QUESTIONS[next_index]
        next_q_tts_url = save_tts_wav(next_q)
        return jsonify({
            "transcript": transcript,
            "ack_text": ack_text,
            "ack_tts_url": ack_tts_url,
            "next_question_index": next_index,
            "next_question_text": next_q,
            "next_question_tts_url": next_q_tts_url,
            "done": False
        })
    else:
        done_text = "Thank you, the survey is complete."
        done_tts_url = save_tts_wav(done_text)
        return jsonify({
            "transcript": transcript,
            "ack_text": ack_text,
            "ack_tts_url": ack_tts_url,
            "done_text": done_text,
            "done_tts_url": done_tts_url,
            "done": True
        })

@app.route("/results", methods=["GET"])
def results():
    if os.path.exists(CSV_FILE):
        return send_file(CSV_FILE, mimetype="text/csv", as_attachment=False, download_name=os.path.basename(CSV_FILE))
    else:
        return "No results yet.", 404

@app.route("/static/audio/<filename>")
def static_audio(filename):
    return send_from_directory(os.path.join(app.root_path, "static", "audio"), filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
