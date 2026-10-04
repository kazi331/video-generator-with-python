import os
BASE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(BASE, 'build')
OUT = os.path.join(BASE, 'output')
os.makedirs(BUILD, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
import json, math, random
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly, lfilter

SR = 44100
meta = json.load(open(os.path.join(BUILD, 'vo_meta.json')))
D = [m + 1.4 for m in meta]
S = [0.0]
for d in D:
    S.append(S[-1] + d)
TOTAL = S[-1]
N = int((TOTAL + 0.3) * SR)
rng = np.random.default_rng(4)
LOGO_T = 3.214

def tarr(dur): return np.arange(int(dur * SR)) / SR

def add(buf, sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i < 0:
        sig = sig[-i:]; i = 0
    n = min(len(sig), N - i)
    if n <= 0: return
    l = gain * (1 - max(pan, 0)); r = gain * (1 + min(pan, 0))
    buf[0, i:i + n] += sig[:n] * l
    buf[1, i:i + n] += sig[:n] * r

def env_ar(n, a, r):
    e = np.ones(n)
    na = max(1, int(a * SR)); nr = max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] = np.minimum(e[-nr:], np.linspace(1, 0, nr))
    return e

def saw(f, dur, harm=7):
    t = tarr(dur); s = np.zeros_like(t)
    for k in range(1, harm + 1):
        s += np.sin(2 * np.pi * f * k * t) / k
    return s * 0.6

# ---------------- music ----------------
BPM = 112; BEAT = 60 / BPM; BAR = BEAT * 4
music = np.zeros((2, N))
CH = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [196.0, 261.63, 329.63], [196.0, 246.94, 293.66]]
ROOT = [110.0, 87.31, 98.0, 98.0]
bars = int(TOTAL / BAR) + 2
drop = 6 * BEAT
for b in range(bars):
    t0 = b * BAR; ch = CH[b % 4]
    for fi, f in enumerate(ch):
        for det, pan in ((0.997, -0.4), (1.003, 0.4)):
            s = saw(f * det, BAR + 0.5) * env_ar(int((BAR + 0.5) * SR), 0.35, 0.5)
            add(music, s, t0, 0.035, pan)
    # arp
    for k in range(8):
        tn = t0 + k * BEAT / 2
        f = ch[[0, 1, 2, 1][k % 4]] * 2
        t = tarr(0.35)
        s = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 11)
        add(music, s, tn, 0.07 * min(1, 0.3 + tn / 3), 0.3 if k % 2 else -0.3)
    # bass + drums after drop
    for k in range(4):
        tn = t0 + k * BEAT
        if tn >= drop - 1e-6:
            t = tarr(0.2)
            fr = 45 + 90 * np.exp(-t * 35)
            kick = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 14)
            add(music, kick, tn, 0.55)
            if k in (1, 3):
                tc = tarr(0.18)
                cl = rng.standard_normal(len(tc))
                cl = np.diff(cl, prepend=0) * np.exp(-tc * 28)
                add(music, cl, tn, 0.2)
    for k in range(8):
        tn = t0 + k * BEAT / 2
        if tn >= drop - 1e-6:
            th = tarr(0.05)
            h = np.diff(rng.standard_normal(len(th)), prepend=0) * np.exp(-th * 90)
            add(music, h, tn, 0.06 if k % 2 else 0.035)
    for tn, ln in ((t0, 0.45), (t0 + 1.5 * BEAT, 0.3), (t0 + 2.5 * BEAT, 0.3)):
        if tn >= drop - 1e-6:
            t = tarr(ln)
            add(music, np.sin(2 * np.pi * ROOT[b % 4] * t) * np.exp(-t * 4) * 0.9, tn, 0.28)
# pre-drop low pad swell keeps tension; global fade out
fade = np.ones(N)
nf = int(2.0 * SR); end = int(TOTAL * SR)
fade[end - nf:end] = np.linspace(1, 0, nf); fade[end:] = 0
music *= fade

# ---------------- voice ----------------
voice = np.zeros((2, N))
for i in range(6):
    a, sr = sf.read(os.path.join(BUILD, f'vo{i}.wav'))
    a = resample_poly(a, 147, 80)
    add(voice, a, S[i] + 0.5, 1.0)
voice *= 1.1

# ---------------- sfx ----------------
sfx = np.zeros((2, N))

def whoosh(dur=0.9, peak=0.5, f0=250, f1=7000):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n)
    # moving bandpass-ish: lowpass with swept cutoff, then highpass differencing
    out = np.zeros(n); y = 0.0
    fc = np.interp(t, [0, dur * peak, dur], [f0, f1, f0 * 1.5])
    a = 1 - np.exp(-2 * np.pi * fc / SR)
    for k in range(n):
        y += a[k] * (x[k] - y); out[k] = y
    out = np.diff(out, prepend=0) * 0.5 + out * 0.5
    e = np.interp(t, [0, dur * peak, dur], [0, 1, 0]) ** 1.5
    return out / (np.abs(out).max() + 1e-9) * e

def pop(f=620, ln=0.18):
    t = tarr(ln)
    return np.sin(2 * np.pi * np.cumsum(f * (1 + 0.8 * np.exp(-t * 40))) / SR) * np.exp(-t * 22)

def click():
    t = tarr(0.05)
    n = np.diff(rng.standard_normal(len(t)), prepend=0) * np.exp(-t * 160)
    return n * 0.8 + np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 120) * 0.6

def ding(f=1318.5, ln=0.9):
    t = tarr(ln)
    return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 1.5 * t) + 0.2 * np.sin(2 * np.pi * f * 2 * t)) * np.exp(-t * 4.5)

def key():
    t = tarr(0.03)
    return np.diff(rng.standard_normal(len(t)), prepend=0) * np.exp(-t * 130)

def tick():
    t = tarr(0.03)
    return np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 150)

# scene transitions
for i in range(1, 6):
    add(sfx, whoosh(0.9, 0.45), S[i] - 0.45, 0.42)
add(sfx, whoosh(0.5, 0.4, 400, 5000), 0.0, 0.2)
# scene 0
add(sfx, pop(300, 0.25), 2.95, 0.5)
add(sfx, ding(1046.5, 1.2), LOGO_T, 0.28)
add(sfx, pop(520), LOGO_T, 0.5)
for k in range(14):
    add(sfx, key(), 0.3 + k * 0.1, 0.18, rng.uniform(-0.3, 0.3))
# scene 1
base = S[1]
for k in range(12):
    add(sfx, key(), base + 0.5 + k * 0.09, 0.16, rng.uniform(-0.3, 0.3))
add(sfx, click(), base + 3.1, 0.7)
add(sfx, pop(700), base + 3.12, 0.4)
add(sfx, ding(1318.5, 1.0), base + 3.3, 0.3)
add(sfx, ding(1975.5, 0.9), base + 3.4, 0.12)
add(sfx, click(), base + 3.9, 0.35)
# scene 2
base = S[2]
for k in range(22):
    add(sfx, tick(), base + 0.7 + k * 0.105, 0.12 * (0.5 + 0.5 * k / 22))
add(sfx, ding(1568, 0.9), base + 3.1, 0.22)
for k in range(7):
    add(sfx, pop(380 + k * 40, 0.12), base + 1.0 + k * 0.12, 0.2)
# scene 3
base = S[3]
add(sfx, pop(500, 0.25), base + 1.45, 0.4)
pent = [523.25, 587.33, 659.25, 783.99, 880.0, 1046.5]
for k in range(16):
    add(sfx, pop(random.Random(k).choice(pent), 0.1), base + 1.8 + k * 0.075, 0.16, rng.uniform(-0.4, 0.4))
t = tarr(0.9)
add(sfx, np.sin(2 * np.pi * np.cumsum(np.linspace(500, 1800, len(t))) / SR) * np.minimum(1, t * 8) * (1 - t / 0.9), base + 3.1, 0.12)
add(sfx, ding(1760, 1.1), base + 4.15, 0.28)
# scene 4
base = S[4]
for k in range(11):
    add(sfx, key(), base + 1.0 + k * 0.109, 0.18, rng.uniform(-0.3, 0.3))
add(sfx, pop(560), base + 1.0, 0.4)
add(sfx, whoosh(0.5, 0.5, 600, 6000), base + 2.55, 0.3)
add(sfx, pop(800), base + 2.75, 0.45)
add(sfx, ding(1568, 0.8), base + 2.85, 0.2)
# scene 5
base = S[5]
add(sfx, ding(1046.5, 1.4), base + 0.1, 0.25)
for tw in (1.6, 1.85, 2.3, 2.55):
    add(sfx, pop(450 + (tw - 1.6) * 120, 0.12), base + tw, 0.28)
add(sfx, whoosh(0.5, 0.4, 500, 6500), base + 3.3, 0.3)
add(sfx, pop(700), base + 3.6, 0.5)
add(sfx, ding(1318.5, 1.6), base + 3.65, 0.3)
add(sfx, ding(1975.5, 1.6), base + 3.75, 0.14)

# ---------------- mix ----------------
env = np.abs(voice).max(axis=0)
k = int(0.18 * SR)
env = np.convolve(env, np.ones(k) / k, mode='same')
env = np.clip(env / (np.percentile(env, 98) + 1e-9), 0, 1)
duck = 1 - 0.55 * env
mix = voice * 1.0 + sfx * 0.9 + music * duck * 1.15
mix = np.tanh(mix * 1.1)
mix = mix / np.abs(mix).max() * 0.92
mix = mix[:, :int((TOTAL + 0.1) * SR)]
sf.write(os.path.join(BUILD, 'mix.wav'), mix.T, SR, subtype='PCM_16')
print('audio done', mix.shape, TOTAL)
