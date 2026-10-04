"""Runs everything: voice -> music/sfx mix -> render frames -> combine into MP4."""
import os, subprocess, sys
BASE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(BASE, "build")
for script in ("tts.py", "audio.py", "render.py"):
    print(f"\n=== {script} ===", flush=True)
    args = [sys.executable, os.path.join(BASE, script)] + (["full"] if script == "render.py" else [])
    subprocess.run(args, check=True, cwd=BASE)
out = os.path.join(BASE, "output", "klip-promo.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(B, "silent.mp4"), "-i", os.path.join(B, "mix.wav"),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
print("\nDone ->", out)
