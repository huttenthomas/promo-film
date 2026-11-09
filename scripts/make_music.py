#!/usr/bin/env python3
"""Generate a royalty-free placeholder soundtrack that follows the film's cuts.

It's a warm pad + soft plucked arpeggio + gentle pulse, with a short swell into
each scene cut and a pared-down ending under the end card. It is intentionally
understated: good enough to ship a draft, but a licensed track will always be
better (pass --music path/to/track.mp3 to render.py).

    python make_music.py out.wav --duration 30 --cuts 0,4,8.5,15,21,25 [--mood bright|calm]
"""
import argparse, wave
import numpy as np

SR = 44100
A4 = 440.0
NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def hz(name):
    """'E4' -> frequency."""
    n, octv = name[:-1], int(name[-1])
    return A4 * 2 ** ((NOTE[n] + 12 * (octv - 4) - 9) / 12)


PROGRESSIONS = {
    # Lydian-leaning, optimistic: Fmaj7 - Am7 - Cmaj9/E - G6sus
    "bright": [["F3", "A3", "C4", "E4"], ["A2", "E3", "G3", "C4"], ["E3", "G3", "B3", "D4"], ["G2", "D3", "E3", "C4"]],
    # Slower, minor-ish and reflective: Am9 - Fmaj7 - C - Gsus
    "calm": [["A2", "E3", "B3", "C4"], ["F2", "C3", "E3", "A3"], ["C3", "G3", "E4", "D4"], ["G2", "D3", "C4", "A3"]],
}


def soft_saw(f, t, harmonics=7):
    out = np.zeros_like(t)
    for k in range(1, harmonics + 1):
        out += np.sin(2 * np.pi * f * k * t) / k ** 1.4
    return out


def env_adsr(n, a, r):
    e = np.ones(n)
    na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    if na: e[:na] = np.linspace(0, 1, na) ** 2
    if nr: e[-nr:] *= np.linspace(1, 0, nr) ** 2
    return e


def reverb(x, seconds=2.2, mix=0.32, seed=7):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 7, n))
    ir[: int(0.012 * SR)] = 0  # pre-delay
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    wet /= np.max(np.abs(wet)) + 1e-9
    return (1 - mix) * x / (np.max(np.abs(x)) + 1e-9) + mix * wet


def make_track(path, duration, cuts, mood="bright"):
    bpm = 96 if mood == "bright" else 80
    beat = 60 / bpm
    bar = beat * 4
    prog = PROGRESSIONS.get(mood, PROGRESSIONS["bright"])
    n = int(duration * SR)
    t_all = np.arange(n) / SR
    pad, pluck, pulse, swell = (np.zeros(n) for _ in range(4))
    end_start = cuts[-1] if len(cuts) > 1 else duration - 4

    # Pad: one chord per bar, overlapping tails for smooth changes.
    nbars = int(np.ceil(duration / bar)) + 1
    for b in range(nbars):
        s0 = int(b * bar * SR)
        if s0 >= n: break
        length = min(n - s0, int((bar + 1.2) * SR))
        t = np.arange(length) / SR
        chord = prog[b % len(prog)]
        seg = sum(soft_saw(hz(x) * (1 + d), t) for x in chord for d in (-0.0025, 0.0025))
        seg *= env_adsr(length, 0.5, 1.2)
        pad[s0:s0 + length] += seg

    # Arpeggio on 8ths, entering after the first cut, thinning out under the end card.
    rng = np.random.default_rng(3)
    start_arp = cuts[1] if len(cuts) > 1 else bar
    step = beat / 2
    k = int(np.ceil(start_arp / step))
    while k * step < end_start + bar:
        t0 = k * step
        chord = prog[int(t0 // bar) % len(prog)]
        note = hz(chord[[0, 2, 3, 1, 2, 3, 1, 3][k % 8]]) * 2
        length = int(1.1 * SR)
        s0 = int(t0 * SR)
        if s0 + length > n: length = n - s0
        if length <= 0: break
        t = np.arange(length) / SR
        vel = 0.75 + 0.25 * rng.random()
        if t0 >= end_start: vel *= 0.5
        pluck[s0:s0 + length] += vel * (np.sin(2 * np.pi * note * t) + 0.3 * np.sin(4 * np.pi * note * t)) * np.exp(-t * 5.5)
        k += 1

    # Soft pulse (sine "kick") on beats 1 and 3, from the second cut until the end card.
    start_pulse = cuts[2] if len(cuts) > 2 else start_arp
    k = int(np.ceil(start_pulse / (beat * 2)))
    while k * beat * 2 < end_start:
        s0 = int(k * beat * 2 * SR)
        length = min(n - s0, int(0.5 * SR))
        t = np.arange(length) / SR
        f = 48 + 40 * np.exp(-t * 30)
        pulse[s0:s0 + length] += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
        k += 1

    # Swell into each cut: filtered noise rising for 0.5s, cut off at the edit.
    for c in cuts[1:]:
        length = int(0.5 * SR)
        s1 = int(c * SR); s0 = max(0, s1 - length)
        noise = rng.standard_normal(s1 - s0)
        noise = np.convolve(noise, np.ones(24) / 24, mode="same")  # crude low-pass
        swell[s0:s1] += noise * np.linspace(0, 1, s1 - s0) ** 3

    # Final low note that rings out under the end card.
    s0 = int(end_start * SR)
    t = np.arange(n - s0) / SR
    tail = np.sin(2 * np.pi * hz(prog[0][0]) / 2 * t) * np.exp(-t * 0.6) * env_adsr(n - s0, 0.05, 1.0)

    def norm(x): return x / (np.max(np.abs(x)) + 1e-9)
    mix = 0.55 * norm(pad) + 0.30 * norm(pluck) + 0.40 * norm(pulse) + 0.10 * norm(swell)
    mix[s0:] += 0.35 * tail
    mix = reverb(mix)
    mix *= env_adsr(n, 0.8, 2.0)
    # Stereo: tiny delay on the right channel for width.
    d = int(0.011 * SR)
    left, right = mix, np.concatenate([np.zeros(d), mix[:-d]])
    st = np.stack([left, right], axis=1)
    st = st / (np.max(np.abs(st)) + 1e-9) * 0.89
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype("<i2").tobytes())
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--duration", type=float, default=30)
    ap.add_argument("--cuts", default="0")
    ap.add_argument("--mood", default="bright", choices=list(PROGRESSIONS))
    a = ap.parse_args()
    make_track(a.out, a.duration, [float(x) for x in a.cuts.split(",")], a.mood)
    print("wrote", a.out)
