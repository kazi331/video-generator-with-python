"""Step 1: generate the voiceover lines with Kokoro (free, local TTS).
Edit LINES to change what the narrator says. Keep 6 lines (one per scene),
or change the scenes in render.py / audio.py to match."""
import os, json
import soundfile as sf
from kokoro_onnx import Kokoro

BASE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(BASE, "build")
os.makedirs(BUILD, exist_ok=True)

VOICE = "af_heart"   # try: af_bella, af_sarah, am_adam, am_michael, bf_emma, bm_george
SPEED = 1.02

LINES = [
    "Long, messy links. Hard to share. Easy to break. Meet Klip.",
    "Turn any long U R L into a clean, short link, in one click.",
    "Then watch every click, with real-time analytics.",
    "Need to share offline? Generate a Q R code instantly.",
    "Make it yours, with custom aliases, and your own domain.",
    "Klip. Short links, big impact. Try it today, at klip dot Kazi Sharif dot dev.",
]

k = Kokoro(os.path.join(BASE, "models", "kokoro-v1.0.onnx"), os.path.join(BASE, "models", "voices-v1.0.bin"))
meta = []
for i, t in enumerate(LINES):
    a, sr = k.create(t, voice=VOICE, speed=SPEED, lang="en-us")
    sf.write(os.path.join(BUILD, f"vo{i}.wav"), a, sr)
    meta.append(len(a) / sr)
    print(f"line {i}: {len(a)/sr:.2f}s")
json.dump(meta, open(os.path.join(BUILD, "vo_meta.json"), "w"))
