#!/usr/bin/env python3
"""Music for promo films: a curated CC0 library, beat analysis, and a music editor that
cuts any track to an exact length the way a picture editor would.

    python music.py list                                  # bundled + fetchable CC0 tracks
    python music.py fetch "Hopeful"                       # download a catalogue track into the cache
    python music.py fit TRACK --length 30 --out bed.wav --grid grid.json

`fit` keeps the track's real opening and its real ending, joined on a matching bar
(chroma + loudness similarity) so the music *finishes* on the end card instead of being
faded out mid-phrase. grid.json lists every beat, the downbeats and the main "lift"
(biggest energy rise) so the picture can be cut on the music.

All library tracks are from FreePD.com (Kevin MacLeod and others), released under CC0 1.0:
free for commercial use, no attribution required. Fetched copies come from the
SoundSafari/CC0-1.0-Music mirror on GitHub.
"""
import argparse, json, random, sys, urllib.parse, urllib.request, warnings
from pathlib import Path
import numpy as np

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
BUNDLED = HERE.parent / "assets" / "music"
CACHE = Path.home() / ".cache" / "promo-film" / "music"
MIRROR = "https://raw.githubusercontent.com/SoundSafari/CC0-1.0-Music/main/freepd.com/"

# mood -> FreePD titles. Bundled ones ship in assets/music; the rest are fetched on demand.
CATALOG = {
    "inspiring": ["Elevate Inspirate", "Inspiration", "Hopeful", "Finally See The Light", "Journey of Hope"],
    "upbeat":    ["Advertime", "Favorite", "Take the Ride", "City Sunshine", "And Here We Go"],
    "calm":      ["Motions", "Shining Stars", "Screen Saver", "Parhelion", "Infinite Wonder"],
    "driving":   ["Rush", "Energizing", "Circuit", "Arpent", "Novus Initium"],
}


def slug(title): return title.lower().replace(" ", "-").replace("'", "")


def bundled_tracks():
    return sorted(BUNDLED.glob("*.mp3")) if BUNDLED.exists() else []


def resolve(spec, mood="inspiring", seed=None):
    """'auto' | 'library:<title or slug>' | path  ->  local file path."""
    if spec in (None, "none"): return None
    if spec == "auto":
        rng = random.Random(seed)
        titles = CATALOG.get(mood, CATALOG["inspiring"])
        local = {p.stem: p for p in bundled_tracks()}
        options = [local[slug(t)] for t in titles if slug(t) in local]
        if options: return rng.choice(options)
        return fetch(rng.choice(titles))
    if spec.startswith("library:"):
        name = spec.split(":", 1)[1]
        for p in bundled_tracks():
            if p.stem == slug(name): return p
        return fetch(name)
    p = Path(spec)
    if not p.exists(): sys.exit(f"music file not found: {spec}")
    return p


def fetch(title):
    titles = {slug(t): t for ts in CATALOG.values() for t in ts}
    title = titles.get(slug(title), title)
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"{slug(title)}.mp3"
    if not out.exists():
        url = MIRROR + urllib.parse.quote(title + ".mp3")
        print(f"fetching {title} (CC0, FreePD) ...")
        urllib.request.urlretrieve(url, out)
    return out


# ---------------------------------------------------------------- analysis
def analyze(y, sr):
    import librosa
    mono = librosa.to_mono(y) if y.ndim > 1 else y
    tempo, beats = librosa.beat.beat_track(y=mono, sr=sr, hop_length=512, tightness=120)
    bt = librosa.frames_to_time(beats, sr=sr, hop_length=512)
    # Downbeat phase: the beat position (of 4) with the most low-end onset energy.
    S = np.abs(librosa.stft(mono, n_fft=2048, hop_length=512))
    low = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S[:40]), sr=sr, hop_length=512)
    vals = [np.mean([low[min(len(low) - 1, f)] for f in beats[ph::4]]) if len(beats[ph::4]) else 0 for ph in range(4)]
    phase = int(np.argmax(vals))
    downs = bt[phase::4]
    chroma = librosa.feature.chroma_cqt(y=mono, sr=sr, hop_length=512)
    rms = librosa.feature.rms(y=mono, hop_length=512)[0]
    return dict(tempo=float(np.atleast_1d(tempo)[0]), beats=bt, downbeats=downs, chroma=chroma, rms=rms, hop=512)


def _seg(feat, sr, hop, a, b):
    fa, fb = int(a * sr / hop), max(int(a * sr / hop) + 1, int(b * sr / hop))
    return feat[..., fa:fb].mean(axis=-1)


def fit(path, length=30.0, sr=44100, reveal_at=None):
    """Return (stereo audio [n,2], grid dict) edited to exactly `length` seconds.

    Searches edits of the form  [s, i) + [j, end)  on downbeats, scoring:
      - how well the bars either side of the join match (harmony + loudness),
      - whether the track's biggest lift lands near `reveal_at` (the product reveal),
      - starting at the top of the track or of a section, never mid-phrase."""
    import librosa
    y, _ = librosa.load(str(path), sr=sr, mono=False)
    if y.ndim == 1: y = np.stack([y, y])
    dur = y.shape[1] / sr
    A = analyze(y, sr)
    downs, bt = A["downbeats"], A["beats"]
    bar = float(np.median(np.diff(downs))) if len(downs) > 2 else 2.0
    rms = A["rms"]; thr = rms.max() * 0.02
    audible_end = (np.nonzero(rms > thr)[0][-1] + 1) * A["hop"] / sr if np.any(rms > thr) else dur
    target = reveal_at if reveal_at is not None else length * 0.27

    # Per-downbeat features: chroma of the bar before, loudness of the bar after, lift ratio.
    D = [float(d) for d in downs]
    cb = [_seg(A["chroma"], sr, A["hop"], max(0, d - bar), d) for d in D]
    ra = [float(_seg(rms, sr, A["hop"], d, d + bar)) for d in D]
    rb = [float(_seg(rms, sr, A["hop"], max(0, d - bar), d)) for d in D]
    liftr = [ra[k] / (rb[k] + 1e-6) if D[k] > bar else 1.0 for k in range(len(D))]
    starts = [k for k in range(len(D)) if D[k] < dur * 0.6]

    def start_pen(k):
        if k == 0: return 0.0                      # top of the track
        if liftr[k] >= 1.25: return 0.12           # top of a new section
        return 0.18 if k % 4 == 0 else 0.4         # phrase-aligned (4 bars) vs mid-phrase

    best = None
    if dur <= length + 0.5:
        best = ("whole", 0.0, 0.0, 0.0, 0.0)
    else:
        for si in starts:
            s0 = D[si]
            for ii in range(si + 1, len(D)):
                head = D[ii] - s0
                if head < length * 0.3: continue
                if head > length - 3 * bar: break
                need = length - head
                # strongest lift inside the head, and where it lands in the edit
                ks = [k for k in range(si + 1, ii) if D[k] - s0 > 2.5]
                if ks:
                    kl = max(ks, key=lambda k: liftr[k]); lpos = D[kl] - s0; lstr = min(liftr[kl], 6.0)
                    lift_score = (lstr - 1) * np.exp(-((lpos - target) / 2.5) ** 2)
                else:
                    lift_score = 0.0
                for jj in range(ii + 1, len(D)):
                    tail = audible_end - D[jj]
                    if tail > need + 1.5 * bar: continue
                    if tail < need - 0.25: break
                    c1, c2 = cb[ii], cb[jj]
                    chroma_sim = float(np.dot(c1, c2) / (np.linalg.norm(c1) * np.linalg.norm(c2) + 1e-9))
                    loud_sim = 1 - abs(ra[ii - 1] - ra[jj - 1]) / (max(ra[ii - 1], ra[jj - 1]) + 1e-9)
                    score = 2.0 * chroma_sim + loud_sim - 0.35 * abs(tail - need) / bar + 0.8 * lift_score \
                            - start_pen(si)
                    if best is None or score > best[4]:
                        best = ("splice", s0, D[ii], D[jj], score)
        if best is None:  # no workable splice: back-time so the real ending lands at `length`
            s = max(0.0, audible_end - length)
            if len(downs): s = float(downs[np.argmin(np.abs(downs - s))])
            best = ("window", s, 0.0, 0.0, 0.0)

    kind, s0, a, b, _ = best
    best_first = float(downs[0]) if len(downs) else 0.0
    xf = int(0.035 * sr)  # 35 ms equal-power crossfade at the join
    if kind == "whole":
        out = y[:, : int(length * sr)]
        mapping = [(0.0, 0.0, dur)]
    elif kind == "window":
        out = y[:, int(s0 * sr): int((s0 + length) * sr)]
        mapping = [(s0, 0.0, length)]
    else:
        h0, h1, t0 = int(s0 * sr), int(a * sr), int(b * sr)
        head, tail = y[:, h0:h1], y[:, t0 - xf:]
        fade = np.sin(np.linspace(0, np.pi / 2, xf)) ** 2
        out = np.concatenate([head[:, :-xf], head[:, -xf:] * (1 - fade) + tail[:, :xf] * fade, tail[:, xf:]], axis=1)
        mapping = [(s0, 0.0, a - s0), (b, a - s0, audible_end - b)]
    n = int(length * sr)
    if out.shape[1] < n: out = np.pad(out, ((0, 0), (0, n - out.shape[1])))
    out = out[:, :n].copy()
    # Gentle 1.2 s release only if the track is still sounding at the very end.
    tail_level = np.abs(out[:, -int(0.3 * sr):]).mean()
    if tail_level > 0.02:
        r = int(1.2 * sr); out[:, -r:] *= np.linspace(1, 0, r) ** 1.5
    fi = int((0.01 if s0 == best_first else 0.35) * sr)   # soft fade-in when entering mid-track
    out[:, :fi] *= np.linspace(0, 1, fi)

    def remap(times):
        res = []
        for src0, dst0, span in mapping:
            for t in times:
                if src0 <= t < src0 + span: res.append(dst0 + (t - src0))
        return sorted(x for x in res if 0 <= x < length)
    # Re-detect the grid on the edited audio itself: beats remapped across a splice can drift,
    # and the end-card cut is the one that most needs to be exactly on the beat.
    try:
        A2 = analyze(out.T if out.shape[0] != 2 else out, sr)
        beats_e = [float(x) for x in A2["beats"] if x < length]
        downs_e = [float(x) for x in A2["downbeats"] if x < length]
        if len(beats_e) < 8: raise ValueError
    except Exception:
        beats_e, downs_e = remap(bt), remap(downs)
    # Keep counting through ring-outs and quiet intros: extend the grid at the track's tempo.
    def extend(xs, step):
        xs = sorted(xs)
        if len(xs) < 2 or step <= 0: return xs
        while xs[-1] + step < length - 0.05: xs.append(xs[-1] + step)
        while xs[0] - step > 0.05: xs.insert(0, xs[0] - step)
        return xs
    ibi = float(np.median(np.diff(beats_e))) if len(beats_e) > 2 else 60 / max(A["tempo"], 1)
    beats_e = extend(beats_e, ibi)
    downs_e = extend(downs_e, ibi * 4)
    # Lift: biggest bar-to-bar loudness rise in the first 70 % (where the "reveal" should land).
    e_rms = np.sqrt(np.convolve((out.mean(axis=0)) ** 2, np.ones(int(0.25 * sr)) / int(0.25 * sr), mode="same"))
    lift, best_rise = None, 0
    for d in downs_e:
        if d < 3 or d > length * 0.7: continue
        before = e_rms[int(max(0, d - bar) * sr): int(d * sr)].mean()
        after = e_rms[int(d * sr): int(min(length, d + bar) * sr)].mean()
        rise = after / (before + 1e-6)
        if rise > best_rise: best_rise, lift = rise, d
    grid = dict(track=Path(path).stem, tempo=round(A["tempo"], 2), bar=round(bar, 4), edit=kind,
                edit_points=[round(s0, 3), round(a, 3), round(b, 3)], beats=[round(x, 4) for x in beats_e],
                downbeats=[round(x, 4) for x in downs_e], lift=round(lift, 4) if lift else None,
                lift_ratio=round(float(best_rise), 2))
    return out.T, grid


def write_wav(path, audio, sr=44100):
    import wave
    a = np.clip(audio, -1, 1)
    peak = np.max(np.abs(a)) + 1e-9
    a = a / peak * 0.95
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((a * 32767).astype("<i2").tobytes())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    f = sub.add_parser("fetch"); f.add_argument("title")
    t = sub.add_parser("fit"); t.add_argument("track"); t.add_argument("--length", type=float, default=30)
    t.add_argument("--out", required=True); t.add_argument("--grid")
    t.add_argument("--reveal-at", type=float, default=None, help="seconds; where the music should lift")
    a = ap.parse_args()
    if a.cmd == "list":
        local = {p.stem for p in bundled_tracks()}
        for mood, ts in CATALOG.items():
            print(f"{mood}:")
            for title in ts: print(f"   {'[bundled] ' if slug(title) in local else '[fetch]   '}{title}")
        print("\nUse in a storyboard as  \"music\": \"library:<title>\"  or  \"auto\" + \"music_mood\".")
    elif a.cmd == "fetch":
        print(fetch(a.title))
    else:
        audio, grid = fit(resolve(a.track), a.length, reveal_at=a.reveal_at)
        write_wav(a.out, audio)
        if a.grid: Path(a.grid).write_text(json.dumps(grid, indent=1))
        print(json.dumps({k: v for k, v in grid.items() if k not in ("beats", "downbeats")}))


if __name__ == "__main__":
    main()
