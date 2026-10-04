"""Downloads the free Kokoro voice model (~350 MB) into ./models
Works around the macOS 'CERTIFICATE_VERIFY_FAILED' error by trying, in order:
  1) Python with the certifi certificate bundle
  2) the system `curl` command (uses the OS certificates)
"""
import os, ssl, shutil, subprocess, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(BASE, "models"), exist_ok=True)
URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"


def via_python(url, path):
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    with urllib.request.urlopen(url, context=ctx) as r, open(path, "wb") as f:
        shutil.copyfileobj(r, f)


def via_curl(url, path):
    subprocess.run(["curl", "-L", "--fail", "-o", path, url], check=True)


for name in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
    path = os.path.join(BASE, "models", name)
    if os.path.exists(path) and os.path.getsize(path) > 1_000_000:
        print("already have", name)
        continue
    print("downloading", name, "...")
    try:
        via_python(URL + name, path)
    except Exception as e:
        print("  python download failed (%s), trying curl..." % type(e).__name__)
        via_curl(URL + name, path)
print("done")
