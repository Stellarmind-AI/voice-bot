# test_edge_tts.py
import edge_tts
import asyncio
import time
import os

async def test_edge_tts():
    text = "Hello! How are you doing? Thanks sweetie, you are too kind"
    start = time.time()

    communicate = edge_tts.Communicate(text, "en-US-AvaMultilingualNeural")
    await communicate.save("edge_test.mp3")

    end = time.time()
    print(f"[Edge TTS] Audio saved as edge_test.mp3 | Latency: {end - start:.2f} seconds")

    # Play audio
    os.system("mpg123 edge_test.mp3" if os.name != "nt" else "start edge_test.mp3")

if __name__ == "__main__":
    asyncio.run(test_edge_tts())

""" 
en-AU-NatashaNeural                Female    General                Friendly, Positive
en-AU-WilliamMultilingualNeural    Male      General                Friendly, Positive
en-CA-ClaraNeural                  Female    General                Friendly, Positive
en-CA-LiamNeural                   Male      General                Friendly, Positive
en-GB-LibbyNeural                  Female    General                Friendly, Positive
en-GB-MaisieNeural                 Female    General                Friendly, Positive
en-GB-RyanNeural                   Male      General                Friendly, Positive
en-GB-SoniaNeural                  Female    General                Friendly, Positive
en-GB-ThomasNeural                 Male      General                Friendly, Positive
en-HK-SamNeural                    Male      General                Friendly, Positive
en-HK-YanNeural                    Female    General                Friendly, Positive
en-IE-ConnorNeural                 Male      General                Friendly, Positive
en-IE-EmilyNeural                  Female    General                Friendly, Positive
en-IN-NeerjaExpressiveNeural       Female    General                Friendly, Positive
en-IN-NeerjaNeural                 Female    General                Friendly, Positive
en-IN-PrabhatNeural                Male      General                Friendly, Positive
en-KE-AsiliaNeural                 Female    General                Friendly, Positive
en-KE-ChilembaNeural               Male      General                Friendly, Positive
en-NG-AbeoNeural                   Male      General                Friendly, Positive
en-NG-EzinneNeural                 Female    General                Friendly, Positive
en-NZ-MitchellNeural               Male      General                Friendly, Positive
en-NZ-MollyNeural                  Female    General                Friendly, Positive
en-PH-JamesNeural                  Male      General                Friendly, Positive
en-PH-RosaNeural                   Female    General                Friendly, Positive
en-SG-LunaNeural                   Female    General                Friendly, Positive
en-SG-WayneNeural                  Male      General                Friendly, Positive
en-TZ-ElimuNeural                  Male      General                Friendly, Positive
en-TZ-ImaniNeural                  Female    General                Friendly, Positive
en-US-AnaNeural                    Female    Cartoon, Conversation  Cute
en-US-AndrewMultilingualNeural     Male      Conversation, Copilot  Warm, Confident, Authentic, Honest
en-US-AndrewNeural                 Male      Conversation, Copilot  Warm, Confident, Authentic, Honest
en-US-AriaNeural                   Female    News, Novel            Positive, Confident
en-US-AvaMultilingualNeural        Female    Conversation, Copilot  Expressive, Caring, Pleasant, Friendly
en-US-AvaNeural                    Female    Conversation, Copilot  Expressive, Caring, Pleasant, Friendly
en-US-BrianMultilingualNeural      Male      Conversation, Copilot  Approachable, Casual, Sincere
en-US-BrianNeural                  Male      Conversation, Copilot  Approachable, Casual, Sincere
en-US-ChristopherNeural            Male      News, Novel            Reliable, Authority
en-US-EmmaMultilingualNeural       Female    Conversation, Copilot  Cheerful, Clear, Conversational
en-US-EmmaNeural                   Female    Conversation, Copilot  Cheerful, Clear, Conversational
en-US-EricNeural                   Male      News, Novel            Rational
en-US-GuyNeural                    Male      News, Novel            Passion
en-US-JennyNeural                  Female    General                Friendly, Considerate, Comfort
en-US-MichelleNeural               Female    News, Novel            Friendly, Pleasant
en-US-RogerNeural                  Male      News, Novel            Lively
en-US-SteffanNeural                Male      News, Novel            Rational
en-ZA-LeahNeural                   Female    General                Friendly, Positive
en-ZA-LukeNeural                   Male      General                Friendly, Positive
"""