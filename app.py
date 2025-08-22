
# #generic bot with gtts/edge_tts
# #deployed on render
# import os
# import uuid
# import datetime
# import pandas as pd
# from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
# from dotenv import load_dotenv
# #from gtts import gTTS
# import requests
# import asyncio
# import edge_tts

# # ---------- Config ----------
# load_dotenv()

# DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
# GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# # Domain/mode controls how the bot talks: "ecommerce", "saas", "education", etc.
# BOT_DOMAIN = os.getenv("BOT_DOMAIN", "general_support")
# # Conversation length (number of assistant questions before closing)
# MAX_TURNS = int(os.getenv("MAX_TURNS", "5"))

# if not DEEPGRAM_API_KEY:
#     raise RuntimeError("Please set DEEPGRAM_API_KEY in .env")
# if not GROQ_API_KEY:
#     raise RuntimeError("Please set GROQ_API_KEY in .env")

# # ---------- App setup ----------
# app = Flask(__name__, static_folder="static", template_folder="templates")

# OUTPUT_DIR = "survey_outputs"
# AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
# os.makedirs(AUDIO_DIR, exist_ok=True)
# os.makedirs(OUTPUT_DIR, exist_ok=True)

# CSV_FILE = os.path.join(OUTPUT_DIR, "survey_results.csv")
# if not os.path.exists(CSV_FILE):
#     pd.DataFrame(
#         columns=["timestamp", "session_id", "turn", "role", "content", "user_audio_path"]
#     ).to_csv(CSV_FILE, index=False)

# # In-memory session store (for demo/dev). For production, use Redis/DB.
# SESSIONS = {}
# # SESSIONS[session_id] = {
# #   "domain": str,
# #   "history": [ {"role": "system/user/assistant", "content": "..."} ],
# #   "turns": int  # number of assistant questions asked so far
# # }

# # ---------- Utilities ----------

# EDGE_TTS_VOICE = "en-US-AvaMultilingualNeural"
# #edge_tts
# def save_tts_mp3(text: str) -> str:
#     """Generate TTS for `text` and save to static/audio as mp3. Return a public URL path."""
#     fname = f"{uuid.uuid4().hex}.mp3"
#     fpath = os.path.join("static", "audio", fname)
#     os.makedirs(os.path.dirname(fpath), exist_ok=True)

#     async def _speak():
#         tts = edge_tts.Communicate(text, EDGE_TTS_VOICE)
#         await tts.save(fpath)

#     asyncio.run(_speak())

#     return f"/static/audio/{fname}"
# """
# GTTS
# def save_tts_mp3(text: str) -> str:
#     #Generate TTS for `text` and save to static/audio as mp3. Return a public URL path.
#     tts = gTTS(text=text, lang='en')
#     fname = f"{uuid.uuid4().hex}.mp3"
#     fpath = os.path.join("static", "audio", fname)
#     os.makedirs(os.path.dirname(fpath), exist_ok=True)
#     tts.save(fpath)
#     return f"/static/audio/{fname}"
# """


# DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"

# def deepgram_transcribe(raw_bytes: bytes, content_type: str) -> str:
#     headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": content_type}
#     params = {"punctuate": "true", "model": "nova-2"}
#     try:
#         resp = requests.post(DEEPGRAM_URL, headers=headers, params=params, data=raw_bytes, timeout=40)
#     except Exception as e:
#         return f"[Deepgram request error: {e}]"

#     if resp.status_code == 200:
#         try:
#             j = resp.json()
#             results = j.get("results", {})
#             channels = results.get("channels", [])
#             if channels and "alternatives" in channels[0]:
#                 alts = channels[0]["alternatives"]
#                 if isinstance(alts, list) and alts:
#                     transcript = alts[0].get("transcript", "")
#                     return transcript if transcript else "[Empty transcript]"
#             return "[Transcript not found]"
#         except Exception as e:
#             return f"[Parsing error: {e}]"
#     else:
#         return f"[Deepgram error: {resp.status_code} {resp.text}]"

# # ---------- LLM brain (Groq) ----------
# GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
# GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")  # open source family; fast & capable

# def _system_prompt(domain: str) -> str:
#     return (
#         f"You are a helpful, concise conversational assistant for a {domain} website. "
#         "Your job is to hold a short, polite conversation to understand the user's intent, satisfaction, and needs. "
#         "Ask one clear question at a time. Keep each question under 25 words. "
#         "If the user asks for help, answer briefly and then ask a follow-up. "
#         "Avoid multiple questions at once. "
#         "When you've gathered enough info (about 3–5 turns), politely wrap up."
#     )

# def groq_chat(messages):
#     headers = {
#         "Authorization": f"Bearer {GROQ_API_KEY}",
#         "Content-Type": "application/json"
#     }
#     payload = {
#         "model": GROQ_MODEL,
#         "messages": messages,
#         "temperature": 0.4,
#     }
#     r = requests.post(GROQ_CHAT_URL, headers=headers, json=payload, timeout=40)
#     if r.status_code != 200:
#         return f"[LLM error: {r.status_code} {r.text}]"
#     try:
#         return r.json()["choices"][0]["message"]["content"].strip()
#     except Exception as e:
#         return f"[LLM parsing error: {e}]"

# def generate_first_question(domain: str):
#     messages = [
#         {"role": "system", "content": _system_prompt(domain)},
#         {"role": "user", "content": "Start the conversation with a friendly, very brief greeting and a single question."}
#     ]
#     return groq_chat(messages)

# def generate_next_turn(history, domain: str):
#     """
#     history: list of {role, content} INCLUDING prior system message.
#     Returns assistant text for the next turn (a single question or a brief answer+question).
#     """
#     return groq_chat(history)

# def generate_closing(history, domain: str):
#     messages = [
#         {"role": "system", "content": _system_prompt(domain)},
#         *history,
#         {"role": "user", "content": "Please wrap up politely in one or two sentences. Offer help and say thanks."}
#     ]
#     return groq_chat(messages)

# # ---------- Routes ----------
# @app.route("/")
# def index():
#     return render_template("index.html")

# @app.route("/api/start", methods=["POST"])
# def api_start():
#     # Create a new session
#     session_id = uuid.uuid4().hex
#     system_msg = {"role": "system", "content": _system_prompt(BOT_DOMAIN)}
#     first_q = generate_first_question(BOT_DOMAIN)

#     SESSIONS[session_id] = {
#         "domain": BOT_DOMAIN,
#         "history": [system_msg, {"role": "assistant", "content": first_q}],
#         "turns": 1  # assistant has asked 1 question
#     }

#     tts_url = save_tts_mp3(first_q)

#     return jsonify({
#         "session_id": session_id,
#         "question_index": 0,  # kept for compatibility with your frontend (not used logically)
#         "question_text": first_q,
#         "question_tts_url": tts_url,
#         "done": False
#     })

# @app.route("/api/answer", methods=["POST"])
# def api_answer():
#     session_id = request.form.get("session_id", "").strip()
#     if not session_id or session_id not in SESSIONS:
#         return jsonify({"error": "Invalid or missing session_id"}), 400

#     state = SESSIONS[session_id]
#     history = state["history"]
#     turns = state["turns"]

#     file = request.files.get("audio")
#     if not file:
#         return jsonify({"error": "No audio provided"}), 400

#     # Save user audio
#     user_audio_fname = f"user_{turns}_{uuid.uuid4().hex}.webm"
#     user_audio_path = os.path.join(AUDIO_DIR, user_audio_fname)
#     os.makedirs(os.path.dirname(user_audio_path), exist_ok=True)
#     file.save(user_audio_path)

#     # Transcribe
#     content_type = file.content_type or "audio/webm"
#     file.stream.seek(0)
#     raw_bytes = file.read()
#     transcript = deepgram_transcribe(raw_bytes, content_type=content_type)

#     # Append to history and log
#     history.append({"role": "user", "content": transcript})
#     pd.DataFrame([{
#         "timestamp": datetime.datetime.now().isoformat(),
#         "session_id": session_id,
#         "turn": turns,
#         "role": "user",
#         "content": transcript,
#         "user_audio_path": user_audio_path
#     }]).to_csv(CSV_FILE, mode="a", header=False, index=False)

#     ack_text = "Thanks for your answer."
#     ack_tts_url = save_tts_mp3(ack_text)

#     # Decide whether to continue or close
#     if turns >= MAX_TURNS:
#         done_text = generate_closing(history, state["domain"])
#         history.append({"role": "assistant", "content": done_text})
#         pd.DataFrame([{
#             "timestamp": datetime.datetime.now().isoformat(),
#             "session_id": session_id,
#             "turn": turns,
#             "role": "assistant",
#             "content": done_text,
#             "user_audio_path": ""
#         }]).to_csv(CSV_FILE, mode="a", header=False, index=False)

#         done_tts_url = save_tts_mp3(done_text)
#         # Optionally clear session to free memory
#         # SESSIONS.pop(session_id, None)

#         return jsonify({
#             "transcript": transcript,
#             "ack_text": ack_text,
#             "ack_tts_url": ack_tts_url,
#             "done_text": done_text,
#             "done_tts_url": done_tts_url,
#             "done": True
#         })
#     else:
#         # Ask next question via LLM
#         next_question = generate_next_turn(history, state["domain"])
#         history.append({"role": "assistant", "content": next_question})
#         state["turns"] += 1

#         pd.DataFrame([{
#             "timestamp": datetime.datetime.now().isoformat(),
#             "session_id": session_id,
#             "turn": state["turns"],
#             "role": "assistant",
#             "content": next_question,
#             "user_audio_path": ""
#         }]).to_csv(CSV_FILE, mode="a", header=False, index=False)

#         next_q_tts_url = save_tts_mp3(next_question)

#         return jsonify({
#             "transcript": transcript,
#             "ack_text": ack_text,
#             "ack_tts_url": ack_tts_url,
#             "next_question_index": state["turns"] - 1,  # for compatibility
#             "next_question_text": next_question,
#             "next_question_tts_url": next_q_tts_url,
#             "done": False
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
#     # Use gunicorn for prod
#     app.run(host="0.0.0.0", port=8000, debug=True)

#generic bot with gtts/edge_tts
#deployed on render
import os
import uuid
import datetime
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
from dotenv import load_dotenv
#from gtts import gTTS
import requests
import asyncio
import edge_tts

# ---------- Config ----------
load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Domain/mode controls how the bot talks: "ecommerce", "saas", "education", etc.
BOT_DOMAIN = os.getenv("BOT_DOMAIN", "survey")  # default changed to survey

if not DEEPGRAM_API_KEY:
    raise RuntimeError("Please set DEEPGRAM_API_KEY in .env")
if not GROQ_API_KEY:
    raise RuntimeError("Please set GROQ_API_KEY in .env")

# ---------- App setup ----------
app = Flask(__name__, static_folder="static", template_folder="templates")

OUTPUT_DIR = "survey_outputs"
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

CSV_FILE = os.path.join(OUTPUT_DIR, "survey_results.csv")
if not os.path.exists(CSV_FILE):
    pd.DataFrame(
        columns=["timestamp", "session_id", "turn", "role", "content", "user_audio_path"]
    ).to_csv(CSV_FILE, index=False)

# In-memory session store (for demo/dev). For production, use Redis/DB.
SESSIONS = {}

# ---------- Utilities ----------

EDGE_TTS_VOICE = "en-US-AvaMultilingualNeural"
#edge_tts
def save_tts_mp3(text: str) -> str:
    """Generate TTS for `text` and save to static/audio as mp3. Return a public URL path."""
    fname = f"{uuid.uuid4().hex}.mp3"
    fpath = os.path.join("static", "audio", fname)
    os.makedirs(os.path.dirname(fpath), exist_ok=True)

    async def _speak():
        tts = edge_tts.Communicate(text, EDGE_TTS_VOICE)
        await tts.save(fpath)

    asyncio.run(_speak())

    return f"/static/audio/{fname}"

"""
GTTS
def save_tts_mp3(text: str) -> str:
    #Generate TTS for `text` and save to static/audio as mp3. Return a public URL path.
    tts = gTTS(text=text, lang='en')
    fname = f"{uuid.uuid4().hex}.mp3"
    fpath = os.path.join("static", "audio", fname)
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    tts.save(fpath)
    return f"/static/audio/{fname}"
"""

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"

def deepgram_transcribe(raw_bytes: bytes, content_type: str) -> str:
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": content_type}
    params = {"punctuate": "true", "model": "nova-2"}
    try:
        resp = requests.post(DEEPGRAM_URL, headers=headers, params=params, data=raw_bytes, timeout=40)
    except Exception as e:
        return f"[Deepgram request error: {e}]"

    if resp.status_code == 200:
        try:
            j = resp.json()
            results = j.get("results", {})
            channels = results.get("channels", [])
            if channels and "alternatives" in channels[0]:
                alts = channels[0]["alternatives"]
                if isinstance(alts, list) and alts:
                    transcript = alts[0].get("transcript", "")
                    return transcript if transcript else "[Empty transcript]"
            return "[Transcript not found]"
        except Exception as e:
            return f"[Parsing error: {e}]"
    else:
        return f"[Deepgram error: {resp.status_code} {resp.text}]"

# ---------- LLM brain (Groq) ----------
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")  # open source family; fast & capable

def _system_prompt(domain: str) -> str:
    return (
        f"You are a helpful, friendly, concise conversational assistant for a {domain} setting. "
        "Your job is to hold a short, polite conversation to understand the user's intent, satisfaction, and needs. "
        "Ask one clear question at a time. Keep each question under 25 words. "
        "If the user asks for help, answer briefly and then ask a follow-up. "
        "Avoid multiple questions at once. "
        "When the user signals they are finished, politely wrap up."
    )

def groq_chat(messages):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.4,
    }
    r = requests.post(GROQ_CHAT_URL, headers=headers, json=payload, timeout=40)
    if r.status_code != 200:
        return f"[LLM error: {r.status_code} {r.text}]"
    try:
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[LLM parsing error: {e}]"

def generate_first_question(domain: str):
    messages = [
        {"role": "system", "content": _system_prompt(domain)},
        {"role": "user", "content": "Start the conversation with a friendly, very brief greeting and a single question."}
    ]
    return groq_chat(messages)

def generate_next_turn(history, domain: str):
    return groq_chat(history)

def generate_closing(history, domain: str):
    messages = [
        {"role": "system", "content": _system_prompt(domain)},
        *history,
        {"role": "user", "content": "Please wrap up politely in one or two sentences. Offer help and say thanks."}
    ]
    return groq_chat(messages)

def check_user_done(history) -> bool:
    """Use LLM to check if user indicated they're finished."""
    messages = [
        {"role": "system", "content": "You are a classifier. Look at the LAST user message only."},
        *history,
        {"role": "user", "content": "Does the last user message mean they want to end or are satisfied? Answer only YES or NO."}
    ]
    result = groq_chat(messages)
    return result.strip().upper().startswith("YES")

# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/start", methods=["POST"])
def api_start():
    session_id = uuid.uuid4().hex
    system_msg = {"role": "system", "content": _system_prompt(BOT_DOMAIN)}
    first_q = generate_first_question(BOT_DOMAIN)

    SESSIONS[session_id] = {
        "domain": BOT_DOMAIN,
        "history": [system_msg, {"role": "assistant", "content": first_q}],
        "turns": 1
    }

    tts_url = save_tts_mp3(first_q)

    return jsonify({
        "session_id": session_id,
        "question_index": 0,
        "question_text": first_q,
        "question_tts_url": tts_url,
        "done": False
    })

@app.route("/api/answer", methods=["POST"])
def api_answer():
    session_id = request.form.get("session_id", "").strip()
    if not session_id or session_id not in SESSIONS:
        return jsonify({"error": "Invalid or missing session_id"}), 400

    state = SESSIONS[session_id]
    history = state["history"]
    turns = state["turns"]

    file = request.files.get("audio")
    if not file:
        return jsonify({"error": "No audio provided"}), 400

    # Save user audio
    user_audio_fname = f"user_{turns}_{uuid.uuid4().hex}.webm"
    user_audio_path = os.path.join(AUDIO_DIR, user_audio_fname)
    os.makedirs(os.path.dirname(user_audio_path), exist_ok=True)
    file.save(user_audio_path)

    # Transcribe
    content_type = file.content_type or "audio/webm"
    file.stream.seek(0)
    raw_bytes = file.read()
    transcript = deepgram_transcribe(raw_bytes, content_type=content_type)

    # Append to history and log
    history.append({"role": "user", "content": transcript})
    pd.DataFrame([{
        "timestamp": datetime.datetime.now().isoformat(),
        "session_id": session_id,
        "turn": turns,
        "role": "user",
        "content": transcript,
        "user_audio_path": user_audio_path
    }]).to_csv(CSV_FILE, mode="a", header=False, index=False)

    ack_text = "Thanks for your answer."
    ack_tts_url = save_tts_mp3(ack_text)

    # LLM-powered decision to end or continue
    if check_user_done(history):
        done_text = generate_closing(history, state["domain"])
        history.append({"role": "assistant", "content": done_text})
        pd.DataFrame([{
            "timestamp": datetime.datetime.now().isoformat(),
            "session_id": session_id,
            "turn": turns,
            "role": "assistant",
            "content": done_text,
            "user_audio_path": ""
        }]).to_csv(CSV_FILE, mode="a", header=False, index=False)

        done_tts_url = save_tts_mp3(done_text)
        return jsonify({
            "transcript": transcript,
            "ack_text": ack_text,
            "ack_tts_url": ack_tts_url,
            "done_text": done_text,
            "done_tts_url": done_tts_url,
            "done": True
        })
    else:
        next_question = generate_next_turn(history, state["domain"])
        history.append({"role": "assistant", "content": next_question})
        state["turns"] += 1

        pd.DataFrame([{
            "timestamp": datetime.datetime.now().isoformat(),
            "session_id": session_id,
            "turn": state["turns"],
            "role": "assistant",
            "content": next_question,
            "user_audio_path": ""
        }]).to_csv(CSV_FILE, mode="a", header=False, index=False)

        next_q_tts_url = save_tts_mp3(next_question)

        return jsonify({
            "transcript": transcript,
            "ack_text": ack_text,
            "ack_tts_url": ack_tts_url,
            "next_question_index": state["turns"] - 1,
            "next_question_text": next_question,
            "next_question_tts_url": next_q_tts_url,
            "done": False
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
