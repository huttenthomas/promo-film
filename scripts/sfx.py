#!/usr/bin/env python3
"""Synthesised sound design for the edit (original, so no licensing questions):
whooshes into transitions, a riser into the reveal, low impacts on the reveal and the logo.
Everything is kept quiet and filtered - it should be felt under the music, not noticed."""
import numpy as np

SR = 44100
_rng = np.random.default_rng(7)


def _lp(x, cutoff):
    """One-pole low-pass with a per-sample cutoff array (Hz)."""
    a = np.exp(-2 * np.pi * np.asarray(cutoff) / SR)
    y = np.empty_like(x); acc = 0.0
    a = np.broadcast_to(a, x.shape)
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc; y[i] = acc
    return y


def whoosh(length=0.7, peak=0.75):
    """Air whoosh: band-limited noise whose brightness and level swell to `peak` (fraction) then fall."""
    n = int(length * SR); t = np.linspace(0, 1, n)
    env = np.where(t < peak, (t / peak) ** 2.2, ((1 - t) / (1 - peak)) ** 1.6)
    noise = _rng.standard_normal(n)
    bright = _lp(noise, 300 + 5200 * env) - 0.6 * _lp(noise, 180)
    return bright * env


def riser(length=1.6):
    """Filtered-noise + rising tone swell that ends exactly at its last sample."""
    n = int(length * SR); t = np.linspace(0, 1, n)
    env = t ** 2.6
    noise = _lp(_rng.standard_normal(n), 200 + 6000 * t ** 2)
    f = 180 * 2 ** (t * 1.6)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    return (noise + tone) * env


def impact(length=2.4):
    """Deep cinematic hit: pitch-dropping sine thump + sub tail + a short air burst."""
    n = int(length * SR); t = np.arange(n) / SR
    f = 38 + 70 * np.exp(-t * 22)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    click = _lp(_rng.standard_normal(n), 2500) * np.exp(-t * 60) * 0.35
    air = _lp(_rng.standard_normal(n), 900) * np.exp(-t * 4.5) * 0.12
    return body + click + air


def place(track, clip, at, gain):
    """Mix `clip` into stereo `track` starting at time `at` (seconds)."""
    s = int(at * SR)
    if s >= len(track): return
    if s < 0: clip, s = clip[-s:], 0
    e = min(len(track), s + len(clip))
    track[s:e, 0] += clip[: e - s] * gain
    track[s:e, 1] += clip[: e - s] * gain * 0.92


def design(scenes, length, reveal_index=None, level="full"):
    """Return stereo sfx bed [n,2] for the timed scene list (each has start, duration, transition).
    level: full (cinematic: whooshes, riser, impacts) | soft (quieter, no riser) | whoosh (transitions only) | none"""
    out = np.zeros((int(length * SR), 2))
    if level == "none": return out
    g = {"full": 1.0, "soft": 0.55, "whoosh": 0.8}.get(level, 1.0)
    norm = lambda x: x / (np.max(np.abs(x)) + 1e-9)
    for i, sc in enumerate(scenes):
        if i == 0: continue
        tr = sc.get("transition", "cut")
        if tr in ("blur", "whip", "dip", "slide", "zoom", "wipe"):
            w = norm(whoosh(0.8 if tr == "whip" else 0.9, 0.7))
            place(out, w, sc["start"] - 0.8 * 0.7, (0.16 if tr in ("whip", "slide", "wipe") else 0.10) * g)
    if level == "whoosh": return out
    if reveal_index is not None:
        r = scenes[reveal_index]["start"]
        if level == "full": place(out, norm(riser(1.6)), r - 1.6, 0.10)
        place(out, norm(impact()), r, 0.30 * g)
    end = scenes[-1]
    if end.get("type") == "end":
        place(out, norm(impact(2.8)), end["start"], 0.26 * g)
    return out
