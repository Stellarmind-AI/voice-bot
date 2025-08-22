# test_gtts.py
from gtts import gTTS
import time
import os

def test_gtts():
    text = "Hello! How are you doing? Do you need help with something."
    start = time.time()

    tts = gTTS(text=text, lang="en")
    tts.save("gtts_test.mp3")

    end = time.time()
    print(f"[gTTS] Audio saved as gtts_test.mp3 | Latency: {end - start:.2f} seconds")

    # Play audio (Linux: mpg123, Mac: afplay, Windows: start)
    os.system("mpg123 gtts_test.mp3" if os.name != "nt" else "start gtts_test.mp3")

if __name__ == "__main__":
    test_gtts()
