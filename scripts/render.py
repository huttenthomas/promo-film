#!/usr/bin/env python3
"""Render a promo-film storyboard (JSON) to an MP4.

    python render.py storyboard.json --check                 # lint only
    python render.py storyboard.json --stills sheet.png      # contact sheet, two frames per shot
    python render.py storyboard.json --out promo.mp4         # full render
Options: --palette NAME|auto|brand:#hex (launch style only)   --music auto|library:<title>|file|generated|none
         --format landscape|square|vertical
         --fps 30   --lens 0..1 (grain/bloom/fringing; default depends on the style's motion)

Requires python3, playwright (+ `playwright install chromium`), ffmpeg.
"""
import argparse, colorsys, json, os, random, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
sys.path.insert(0, str(HERE))
from scan_project import img_size  # noqa: E402
import style as stylemod  # noqa: E402

SCENE_TYPES = {"shot", "title", "end", "pieces", "list", "quote"}
MOVES = {"macro-drift", "macro-rack", "sweep", "tilt-up", "push-in", "pull-back", "float", "hero-turn", "tilt",
         "drift", "zoom-in", "zoom-out", "pan-down", "pan-across", "rise"}
FLAT_MOVES = {"drift", "zoom-in", "zoom-out", "pan-down", "pan-across", "rise", "push-in"}
DEVICES = {"phone", "browser", "window", "panel", "none"}
TRANSITIONS = {"cut", "blur", "whip", "dip", "slide"}
ROLES = {"hook", "reveal", "benefit", "proof", "cta", "intro", "work", "service", "about", "process"}
MACRO = {"macro-drift", "macro-rack", "tilt-up"}
AI_WORDS = ("unleash", "supercharge", "elevate your", "seamless", "revolutioniz", "next-gen", "game-chang",
            "the future of", "empower", "cutting-edge", "unlock", "skyrocket", "effortless", "passionate about",
            "crafting digital experiences", "pixel-perfect", "synergy")


def words(s): return len(str(s or "").split())


# Story arcs by subject. Each entry: roles that should appear (in roughly this order).
ARCS = {
    "product": ["hook", "reveal", "benefit", "cta"],
    "library": ["hook", "reveal", "benefit", "cta"],
    "person":  ["intro", "service", "work", "cta"],
    "service": ["hook", "reveal", "service", "work", "cta"],
}


def lint(sb, base):
    errs, warns = [], []
    scenes = sb.get("scenes") or []
    if not scenes: errs.append("storyboard has no scenes")
    total = sum(float(s.get("duration", 0)) for s in scenes)
    target = float(sb.get("target_duration", 30))
    if abs(total - target) > 0.51:
        errs.append(f"scene durations sum to {total:.2f}s, expected {target:g}s")
    staging = (sb.get("style") or {}).get("staging") if isinstance(sb.get("style"), dict) else None
    shots = [s for s in scenes if s.get("type") == "shot"]
    if len(shots) >= 3 and len({s.get("move") for s in shots}) < 3:
        warns.append("camera moves repeat a lot - vary them so shots don't feel templated")
    for i, s in enumerate(scenes):
        tag = f"scene {i+1} ({s.get('type')})"
        t, d = s.get("type"), float(s.get("duration", 0))
        if t not in SCENE_TYPES:
            errs.append(f"{tag}: unknown type; use one of {sorted(SCENE_TYPES)}"); continue
        if s.get("role") and s["role"] not in ROLES: errs.append(f"{tag}: role must be one of {sorted(ROLES)}")
        if s.get("transition") and s["transition"] not in TRANSITIONS:
            errs.append(f"{tag}: transition must be one of {sorted(TRANSITIONS)}")
        if t in ("shot", "pieces"):
            if t == "shot" and not s.get("screen") and not s.get("terminal"):
                errs.append(f"{tag}: needs 'screen' (image path) or 'terminal'")
            if t == "pieces" and not s.get("screen"): errs.append(f"{tag}: needs 'screen' to cut pieces from")
            if s.get("screen") and not (base / s["screen"]).exists():
                errs.append(f"{tag}: screen not found: {s['screen']}")
        if t == "shot":
            dev = s.get("device", staging or "panel")
            if dev not in DEVICES: errs.append(f"{tag}: device must be one of {sorted(DEVICES)}")
            if s.get("move") and s["move"] not in MOVES and not s.get("camera"):
                errs.append(f"{tag}: unknown move {s['move']!r}; use one of {sorted(MOVES)}")
            if dev == "none" and s.get("move") and s["move"] not in FLAT_MOVES:
                warns.append(f"{tag}: full-bleed shots only pan/zoom; use one of {sorted(FLAT_MOVES)}")
            if not 2.0 <= d <= 7: warns.append(f"{tag}: {d}s - shots read best between 2 and 7 seconds")
            if s.get("screen") and (base / s["screen"]).exists():
                sz = img_size(base / s["screen"])
                if sz and dev == "phone" and sz[0] < 700: warns.append(f"{tag}: screen only {sz[0]}px wide - capture at 3x")
                if sz and dev in ("browser", "none") and sz[0] < 1800: warns.append(f"{tag}: screen only {sz[0]}px wide - capture at 2x")
            cap = s.get("caption")
            if cap:
                side = "left" if isinstance(cap, str) else cap.get("side", "left")
                if side in ("left", "right") and s.get("move") in MACRO:
                    warns.append(f"{tag}: side caption on a close-up will overlap; use side 'over' or a wider move")
        if t == "pieces":
            items = s.get("items") or []
            if not 1 <= len(items) <= 6: errs.append(f"{tag}: needs 1-6 items")
            for it in items:
                c = it.get("crop")
                if c and (len(c) != 4 or not all(0 <= v <= 1 for v in c)): errs.append(f"{tag}: crop must be [x, y, w, h] fractions")
        if t == "list":
            n = len(s.get("items") or [])
            if not 2 <= n <= 6: errs.append(f"{tag}: lists need 2-6 items")
            if d < 1.2 + 0.5 * n: warns.append(f"{tag}: {n} items in {d}s will feel rushed")
            for it in s.get("items") or []:
                if words(it if isinstance(it, str) else it.get("text")) > 5: warns.append(f"{tag}: list item over 5 words: {it!r}")
        if t == "quote":
            if not s.get("text") or not s.get("author"): errs.append(f"{tag}: quote needs text and author")
            if not s.get("source"): warns.append(f"{tag}: add 'source' (where this quote appears) - only use real quotes")
            if words(s.get("text")) > 22: warns.append(f"{tag}: quote is long; trim to the strongest sentence")
        if t == "title":
            if not s.get("text"): errs.append(f"{tag}: missing text")
            if words(s.get("text")) > 8: warns.append(f"{tag}: {words(s['text'])} words - keep titles to 8 or fewer")
        if t == "end":
            if not s.get("name") and not s.get("logo"): errs.append(f"{tag}: needs name or logo")
            if s.get("logo") and not (base / s["logo"]).exists(): errs.append(f"{tag}: logo not found: {s['logo']}")
            if d < 3: warns.append(f"{tag}: give the end card at least 3s")
        cap = s.get("caption")
        if cap:
            text = cap if isinstance(cap, str) else cap.get("text", "")
            if words(text) > 7: warns.append(f"{tag}: caption has {words(text)} words - keep it to 7 or fewer")
    if scenes and scenes[-1].get("type") != "end": warns.append("last scene is not an 'end' card")
    # story arc
    subject = sb.get("subject", "product")
    roles = [s.get("role") for s in scenes]
    if subject not in ARCS: errs.append(f"subject must be one of {sorted(ARCS)}")
    elif not any(roles):
        warns.append("story: no scene roles set - see the arcs in references/storyboard.md")
    else:
        for need in ARCS[subject]:
            if need not in roles: warns.append(f"story ({subject}): no '{need}' scene")
        if subject in ("product", "library") and roles.count("benefit") < 2:
            warns.append("story: fewer than 2 'benefit' scenes - say what the viewer gets")
        if scenes and scenes[-1].get("type") == "end" and not scenes[-1].get("cta"):
            warns.append("story: end card has no 'cta' - tell viewers what to do next")
    parts = []
    for s in scenes:
        parts += [s.get("text", ""), s.get("tagline", ""), s.get("cta", "")]
        if s.get("type") == "list": parts += [it if isinstance(it, str) else it.get("text", "") for it in s.get("items") or []]
        cap = s.get("caption")
        parts.append(cap.get("text", "") if isinstance(cap, dict) else (cap or ""))
    copy = " ".join(str(x) for x in parts).lower()
    for w in AI_WORDS:
        if w in copy: warns.append(f"copy uses '{w}' - reads as generated; say the concrete thing instead")
    if "!" in copy: warns.append("exclamation mark in copy - let the work carry the energy")
    blob = json.dumps(sb).lower()
    for tm in ("iphone", "macbook", "ipad", "sf pro"):
        if tm in blob: warns.append(f"storyboard mentions '{tm}' - keep Apple trademarks out of the film")
    return errs, warns


def reveal_index(scenes):
    """The scene the music's lift should land on: the product reveal, or (for people/services)
    the first scene that shows the work."""
    for roles in (("reveal",), ("work", "service")):
        for i, s in enumerate(scenes):
            if i > 0 and s.get("role") in roles: return i
    return None


def time_to_music(sb, grid):
    """Snap every cut to the music: the reveal lands on the lift (if close), CTA/end and reveal on
    downbeats, everything else on the nearest beat. Durations are rewritten in place."""
    scenes = sb["scenes"]
    beats, downs = grid.get("beats") or [], grid.get("downbeats") or []
    if not beats: return
    total = sum(float(s["duration"]) for s in scenes)
    t, bounds = 0.0, []
    for s in scenes[:-1]:
        t += float(s["duration"]); bounds.append(t)
    bar = grid.get("bar") or 2.0
    ri = reveal_index(scenes)
    durs = [float(s["duration"]) for s in scenes]
    snapped, prev = [], 0.0
    for k, b in enumerate(bounds):
        nxt = scenes[k + 1]
        # Never squeeze a scene below ~75 % of its planned length (or 1.6 s).
        lo = prev + max(1.6, 0.75 * durs[k])
        hi = total - max(1.6, 0.75 * sum(durs[k + 1:]) / max(1, len(durs) - k - 1)) * (len(bounds) - k)
        major = (k + 1) == ri or nxt.get("role") in ("reveal", "cta") or nxt.get("type") == "end"
        pick = None
        stretch = min(4.0, max(1.0, 0.6 * durs[k]))   # never stretch/squeeze the previous scene by more than ~60 %
        if (k + 1) == ri and grid.get("lift") and abs(grid["lift"] - b) <= stretch and lo <= grid["lift"] <= hi:
            pick = grid["lift"]                                  # reveal on the musical lift
        if pick is None and major:
            near = [d for d in downs if lo <= d <= hi and abs(d - b) <= 0.5 * bar]
            if near: pick = min(near, key=lambda d: abs(d - b))  # big moments on a downbeat
        if pick is None:
            near = [x for x in beats if lo <= x <= hi]
            pick = min(near, key=lambda x: abs(x - b)) if near else b
        snapped.append(pick); prev = pick
    edges = [0.0] + snapped + [total]
    for i, s in enumerate(scenes):
        s["duration"] = round(edges[i + 1] - edges[i], 4)
    sb["beats"] = beats


def prepare_music(sb, sb_path, total):
    """Resolve and fit the music; returns (wav_path or None, grid)."""
    spec = sb.get("music", "auto")
    if spec in (None, "none"): return None, {}
    if spec == "generated":
        return "generated", {}
    import music
    ri, reveal_at = reveal_index(sb["scenes"]), None
    if ri is not None: reveal_at = sum(float(s["duration"]) for s in sb["scenes"][:ri])
    mood = sb.get("music_mood") or {"cinematic": "inspiring", "snappy": "driving", "playful": "upbeat",
                                     "calm": "calm"}.get(sb["style"].get("motion"), "inspiring")
    track = music.resolve(spec, mood)
    print(f"music: {track.stem} (CC0)" if "assets/music" in str(track) or ".cache" in str(track) else f"music: {track}")
    audio, grid = music.fit(track, total, reveal_at=reveal_at)
    out = Path(tempfile.mkdtemp()) / "bed.wav"
    music.write_wav(out, audio)
    print(f"music edit: {grid['edit']} at {grid['edit_points']}, {grid['tempo']:.0f} bpm, lift at {grid['lift']}s")
    return out, grid


def build_page(sb, sb_path, workdir):
    base = sb_path.parent
    media = workdir / "media"; media.mkdir()
    sb = json.loads(json.dumps(sb))
    for i, s in enumerate(sb["scenes"]):
        for key in ("screen", "logo"):
            if s.get(key):
                src = (base / s[key]).resolve()
                dst = media / f"{i}_{key}{src.suffix}"
                shutil.copy(src, dst)
                s[key] = f"media/{dst.name}"
                if key == "screen":
                    s["_nat"] = list(img_size(src) or (1179, 2556))
    html = (ASSETS / "template.html").read_text()
    fonts = {role: (fam, [(Path(p), w, st) for p, w, st in files], src) for role, (fam, files, src) in sb.pop("_fonts").items()}
    html = html.replace("<!--FONTFACES-->", stylemod.fontface_css(fonts, workdir))
    inject = "<script>window.__STORYBOARD__ = " + json.dumps(sb).replace("</", "<\\/") + ";</script>"
    out = workdir / "index.html"; out.write_text(html.replace("<body>", "<body>\n" + inject, 1))
    return out


def open_page(pw, page_path, w, h):
    browser = pw.chromium.launch(args=["--font-render-hinting=none", "--allow-file-access-from-files",
                                       "--force-color-profile=srgb"])
    page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(page_path.as_uri())
    page.evaluate("window.__ready")
    if errors: raise RuntimeError("template error: " + "; ".join(errors))
    return browser, page


def settle(page):
    """Wait two animation frames so Chromium finishes rasterising after big camera jumps
    (without this, close-ups occasionally capture un-rasterised black tiles)."""
    page.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")


def lens_filter(w, h, lens):
    """Post-processing that makes it look shot rather than generated: bloom, a hair of colour
    fringing, vignette and moving film grain. Deterministic (fixed noise seed)."""
    if lens <= 0: return "format=yuv420p"
    sigma = max(4, h * 0.018)
    shift = max(1, round(h / 1080 * lens))
    grain = max(1, round(5 * lens))
    return (f"split[a][b];[b]gblur=sigma={sigma:.1f},format=gbrp[g];[a]format=gbrp[a2];"
            f"[a2][g]blend=all_mode=screen:all_opacity={0.14*lens:.3f},"
            f"rgbashift=rh=-{shift}:bh={shift},"
            f"vignette=angle=PI/5.5,"
            f"noise=alls={grain}:allf=t:all_seed=1337,format=yuv420p")


def render_stills(sb, sb_path, out, w, h, lens):
    from playwright.sync_api import sync_playwright
    with tempfile.TemporaryDirectory() as td, sync_playwright() as pw:
        td = Path(td)
        browser, page = open_page(pw, build_page(sb, sb_path, td), w, h)
        frames, t0 = [], 0.0
        for i, s in enumerate(sb["scenes"]):
            d = float(s["duration"])
            for j, frac in enumerate((0.15, 0.85) if s["type"] == "shot" else (0.8,)):
                page.evaluate(f"renderAt({t0 + d * frac})"); settle(page)
                f = td / f"s{i:02d}_{j}.png"; page.screenshot(path=str(f)); frames.append(f)
            t0 += d
        browser.close()
        # Apply the lens look to each still so the sheet matches the final film.
        graded = []
        for f in frames:
            g = f.with_name(f.stem + "_g.png")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(f), "-vf",
                            lens_filter(w, h, lens).replace("format=yuv420p", "format=rgb24"), str(g)], check=True)
            graded.append(g)
        cols = 4 if len(graded) > 9 else 3
        rows = -(-len(graded) // cols)
        tw = (w // cols) // 2 * 2; th = round(tw * h / w) // 2 * 2
        args = ["ffmpeg", "-y", "-loglevel", "error"]
        for f in graded: args += ["-i", str(f)]
        filt = "".join(f"[{i}:v]scale={tw}:{th},drawbox=c=0x222222:t=2[s{i}];" for i in range(len(graded)))
        pad = cols * rows - len(graded)
        for k in range(pad): filt += f"color=c=black:s={tw}x{th}:d=1[p{k}];"
        labels = "".join(f"[s{i}]" for i in range(len(graded))) + "".join(f"[p{k}]" for k in range(pad))
        layout = "|".join(f"{'+'.join(['w0'] * (n % cols)) or '0'}_{'+'.join(['h0'] * (n // cols)) or '0'}" for n in range(cols * rows))
        filt += f"{labels}xstack=inputs={cols*rows}:layout={layout}"
        subprocess.run(args + ["-filter_complex", filt, "-frames:v", "1", "-update", "1", str(out)], check=True)
    print(f"stills -> {out}  (shots show two frames: start and end of the camera move)")


def _render_chunk(job):
    """Worker: render frames [a, b) in its own Chromium and encode a near-lossless segment."""
    sb, sb_path, w, h, fps, a, b, seg = job
    from playwright.sync_api import sync_playwright
    with tempfile.TemporaryDirectory() as td, sync_playwright() as pw:
        browser, page = open_page(pw, build_page(sb, Path(sb_path), Path(td)), w, h)
        enc = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "png", "-i", "-",
             "-c:v", "libx264", "-preset", "ultrafast", "-crf", "6", "-pix_fmt", "yuv444p", seg], stdin=subprocess.PIPE)
        for i in range(a, b):
            page.evaluate(f"renderAt({i / fps})"); settle(page)
            enc.stdin.write(page.screenshot(type="png"))
        enc.stdin.close(); enc.wait(); browser.close()
        if enc.returncode: raise RuntimeError("ffmpeg failed on segment " + seg)
    return b - a


def render_video(sb, sb_path, out, w, h, fps, music, lens, workers):
    import concurrent.futures as cf, multiprocessing as mp, time
    total = sum(float(s["duration"]) for s in sb["scenes"])
    n = int(round(total * fps))
    workers = max(1, min(workers, n // fps))
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        bounds = [round(n * k / workers) for k in range(workers + 1)]
        jobs = [(sb, str(sb_path), w, h, fps, bounds[k], bounds[k + 1], str(td / f"seg{k:02d}.mkv")) for k in range(workers)]
        t0, done = time.time(), 0
        print(f"rendering {n} frames with {workers} worker(s)...")
        with cf.ProcessPoolExecutor(workers, mp_context=mp.get_context("spawn")) as ex:
            for fut in cf.as_completed([ex.submit(_render_chunk, j) for j in jobs]):
                done += fut.result()
                print(f"  {done}/{n} frames  ({time.time() - t0:.0f}s)", flush=True)
        (td / "list.txt").write_text("".join(f"file '{j[-1]}'\n" for j in jobs))
        silent = td / "video.mp4"
        # Final pass: lens look + delivery encode. Bitrate is capped because film grain is
        # expensive to encode and would otherwise balloon the file to hundreds of MB.
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(td / "list.txt"),
                        "-vf", lens_filter(w, h, lens), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                        "-maxrate", "10M", "-bufsize", "20M", "-tune", "grain" if lens > 0 else "film",
                        "-pix_fmt", "yuv420p", "-r", str(fps), "-movflags", "+faststart", str(silent)], check=True)

        track = music
        if track == "generated":
            from make_music import make_track
            track = td / "music.wav"
            cuts, t = [], 0.0
            for sc in sb["scenes"]:
                cuts.append(t); t += float(sc["duration"])
            make_track(str(track), total, cuts, mood=sb.get("music_mood", "calm"))
        if track and sb.get("sound_design", True) and sb["style"].get("sound_design") != "none":
            # Lay the sound design under the music.
            import numpy as np, wave, sfx
            timed, t = [], 0.0
            for sc in sb["scenes"]:
                timed.append({**sc, "start": t, "transition": sc.get("transition", sb.get("default_transition", "cut"))}); t += float(sc["duration"])
            ri = reveal_index(sb["scenes"])
            fx = sfx.design(timed, total, ri, level=sb["style"].get("sound_design", "full"))
            fxp = td / "sfx.wav"
            with wave.open(str(fxp), "wb") as wf:
                wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sfx.SR)
                wf.writeframes((np.clip(fx, -1, 1) * 32767).astype("<i2").tobytes())
            mixed = td / "mix.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(track), "-i", str(fxp), "-filter_complex",
                            "[0:a][1:a]amix=inputs=2:normalize=0:weights=1 1[a]", "-map", "[a]", str(mixed)], check=True)
            track = mixed
        if track:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(track),
                            "-filter_complex", f"[1:a]atrim=0:{total},loudnorm=I=-14:TP=-1.0:LRA=9[a]",
                            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
                            "-shortest", "-movflags", "+faststart", str(out)], check=True)
        else:
            shutil.copy(silent, out)
    print(f"video -> {out}  ({total:g}s, {w}x{h} @ {fps}fps, {out.stat().st_size/1e6:.1f} MB)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("storyboard")
    ap.add_argument("--out", default="promo.mp4")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--stills", metavar="PNG")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--palette", default=None)
    ap.add_argument("--music", default=None)
    ap.add_argument("--lens", type=float, default=None)
    ap.add_argument("--format", choices=["landscape", "square", "vertical"], default=None)
    ap.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1),
                    help="parallel Chromium renderers (default: min(4, CPU cores))")
    a = ap.parse_args()

    sb_path = Path(a.storyboard).resolve()
    sb = json.loads(sb_path.read_text())
    fmt = a.format or sb.get("format", "landscape")
    w, h = {"landscape": (1920, 1080), "square": (1080, 1080), "vertical": (1080, 1920)}[fmt]
    sb["width"], sb["height"] = w, h

    errs, warns = lint(sb, sb_path.parent)
    for m in warns: print("warn:", m)
    for m in errs: print("ERROR:", m)
    if errs: sys.exit(1)
    if a.check: print("storyboard OK"); return
    if not shutil.which("ffmpeg"): sys.exit("ffmpeg not found on PATH")

    st, fonts, info = stylemod.resolve(sb.get("style", "launch"), sb_path.parent, a.palette or sb.get("palette"))
    for line in info: print(line)
    if a.lens is not None: st["lens"] = a.lens
    if "dof" in sb: st["dof_global"] = sb["dof"]
    sb["style"] = st
    sb["_fonts"] = {role: (fam, [(str(p), w, sty) for p, w, sty in files], src) for role, (fam, files, src) in fonts.items()}
    lens = float(st["lens"])
    if a.music is not None: sb["music"] = a.music
    total = sum(float(s["duration"]) for s in sb["scenes"])
    track, grid = prepare_music(sb, sb_path, total)
    if grid:
        time_to_music(sb, grid)
        print("cuts on the music: " + ", ".join(f"{sum(float(x['duration']) for x in sb['scenes'][:i+1]):.2f}" for i in range(len(sb['scenes']) - 1)))
    if a.stills:
        render_stills(sb, sb_path, Path(a.stills).resolve(), w, h, lens); return
    render_video(sb, sb_path, Path(a.out).resolve(), w, h, a.fps, track, lens, a.workers)
    if st.get("_palette"): stylemod.remember_palette(st["_palette"])


if __name__ == "__main__":
    main()
