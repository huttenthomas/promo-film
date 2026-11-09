#!/usr/bin/env python3
"""Resolve a storyboard's `style` into concrete colours, type, motion and font files.

A style is normally the project's own aesthetic, produced by extract_style.py and saved as
style.json next to the storyboard ("style": "style.json"). It can also be an inline object, or the
preset "launch" (dark cinematic launch-film look with a rotating curated palette).

Fonts are resolved in this order: files listed in the style (the project's own font files) ->
Fontsource (Google Fonts mirror on the npm registry, cached) -> bundled Inter / JetBrains Mono.
"""
import colorsys, io, json, random, re, shutil, sys, tarfile, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
CACHE = Path.home() / ".cache" / "promo-film"
HISTORY = CACHE / "palette_history.json"

# Curated palettes for the "launch" preset (deep edge, mid, lit centre, text).
PALETTES = {
    "cobalt": ("#020733", "#0a2ccf", "#2f62ff", "#ffffff"), "emerald": ("#011510", "#0a5e43", "#17946a", "#ffffff"),
    "oxblood": ("#160205", "#5e0d1b", "#9b2236", "#ffffff"), "tangerine": ("#2a0b02", "#b8430f", "#f2742c", "#ffffff"),
    "teal": ("#011417", "#0a535a", "#16909a", "#ffffff"), "ochre": ("#1c1202", "#7f5306", "#c9921a", "#ffffff"),
    "graphite": ("#040405", "#1b1d22", "#3a3e48", "#ffffff"), "crimson": ("#1a0203", "#8f0e1a", "#d42536", "#ffffff"),
    "forest": ("#030c05", "#1a4321", "#367540", "#ffffff"), "slate": ("#05090f", "#203248", "#46658c", "#ffffff"),
    "bone": ("#b9b1a2", "#ddd6c8", "#f4f1ea", "#1d1d1f"), "fog": ("#a9afb8", "#d5d9df", "#f2f4f6", "#1d1d1f"),
}

LENS_BY_MOTION = {"cinematic": 1.0, "calm": 0.45, "snappy": 0.0, "playful": 0.0}
SFX_BY_MOTION = {"cinematic": "full", "calm": "soft", "snappy": "whoosh", "playful": "soft"}
GENERIC = {"sans-serif", "serif", "monospace", "system-ui", "ui-sans-serif", "ui-serif", "ui-monospace", "cursive",
           "-apple-system", "blinkmacsystemfont", "segoe ui", "helvetica neue", "helvetica", "arial", "roboto mono",
           "apple color emoji", "segoe ui emoji", "noto color emoji", "inherit", "initial"}
SYSTEM_FALLBACK = {"display": "Inter", "body": "Inter", "mono": "JetBrains Mono"}


# ---------------------------------------------------------------- colour helpers
def _rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3: h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _hex(rgb): return "#%02x%02x%02x" % tuple(max(0, min(255, round(c * 255))) for c in rgb)


def mix(a, b, t):
    A, B = _rgb(a), _rgb(b)
    return _hex(tuple(x + (y - x) * t for x, y in zip(A, B)))


def luminance(h):
    def ch(c): return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def on_color(bg):
    return "#ffffff" if contrast(bg, "#ffffff") >= contrast(bg, "#111111") else "#111111"


# ---------------------------------------------------------------- palettes (launch preset)
def pick_palette(spec):
    if spec and spec.startswith("brand:"):
        r, g, b = _rgb(spec[6:]); h, l, s = colorsys.rgb_to_hls(r, g, b); s = max(0.45, min(s, 0.85))
        mk = lambda L: _hex(colorsys.hls_to_rgb(h, L, s))
        return spec, (mk(0.06), mk(0.30), mk(0.50), "#ffffff")
    if spec and spec != "auto":
        if spec not in PALETTES: sys.exit(f"unknown palette {spec!r}; choose from {', '.join(PALETTES)}")
        return spec, PALETTES[spec]
    try: hist = json.loads(HISTORY.read_text())
    except Exception: hist = []
    name = random.choice([p for p in PALETTES if p not in hist[-5:]] or list(PALETTES))
    return name, PALETTES[name]


def remember_palette(name):
    if name not in PALETTES: return
    try: hist = json.loads(HISTORY.read_text())
    except Exception: hist = []
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps((hist + [name])[-12:]))


# ---------------------------------------------------------------- fonts
def _slug(family): return re.sub(r"[^a-z0-9]+", "-", family.lower()).strip("-")


def fontsource(family, weights=(400, 500, 600, 700, 800)):
    """Fetch a Google font from Fontsource (npm registry). Returns [(path, weight, style)] or []."""
    slug = _slug(family)
    dest = CACHE / "fonts" / slug
    have = sorted(dest.glob("*.woff2")) if dest.exists() else []
    if not have:
        try:
            meta = json.load(urllib.request.urlopen(f"https://registry.npmjs.org/@fontsource/{slug}/latest", timeout=20))
            data = urllib.request.urlopen(meta["dist"]["tarball"], timeout=60).read()
        except Exception:
            return []
        dest.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            for m in tar.getmembers():
                mm = re.search(rf"files/{re.escape(slug)}-latin-(\d+)-(normal|italic)\.woff2$", m.name)
                if mm and mm.group(2) == "normal" and int(mm.group(1)) in weights:
                    (dest / Path(m.name).name).write_bytes(tar.extractfile(m).read())
        have = sorted(dest.glob("*.woff2"))
    out = []
    for f in have:
        mm = re.search(r"-latin-(\d+)-(normal|italic)\.woff2$", f.name)
        if mm: out.append((f, int(mm.group(1)), mm.group(2)))
    return out


def bundled(role):
    F = ASSETS / "fonts"
    if role == "mono":
        return [(F / "jetbrains-mono-latin-400-normal.woff2", 400, "normal"), (F / "jetbrains-mono-latin-500-normal.woff2", 500, "normal")]
    return [(F / "InterDisplay-Regular.otf", 400, "normal"), (F / "InterDisplay-Medium.otf", 500, "normal"),
            (F / "InterDisplay-SemiBold.otf", 600, "normal"), (F / "InterDisplay-Bold.otf", 700, "normal")]


def resolve_font(spec, role, base):
    """spec: "Family" | {"family": ..., "files": [{"path", "weight", "style"}]} -> (family, files, source)."""
    if spec is None: spec = SYSTEM_FALLBACK[role]
    if isinstance(spec, str): spec = {"family": spec}
    fam = spec.get("family") or SYSTEM_FALLBACK[role]
    files = []
    for f in spec.get("files", []):
        p = Path(f["path"]); p = p if p.is_absolute() else base / p
        if p.exists(): files.append((p, int(f.get("weight", 400)), f.get("style", "normal")))
    if files: return fam, files, "project files"
    if fam.lower() in ("inter", "inter display") and role != "mono": return fam, bundled(role), "bundled"
    if fam.lower() in ("jetbrains mono",) and role == "mono": return fam, bundled(role), "bundled"
    if fam.lower() not in GENERIC:
        got = fontsource(fam)
        if got: return fam, got, "fontsource"
    return SYSTEM_FALLBACK[role], bundled(role), f"fallback (could not find '{fam}')"


def fontface_css(fonts, workdir):
    """Copy font files into workdir/fonts and return @font-face CSS for PF Display/Body/Mono."""
    out = workdir / "fonts"; out.mkdir(exist_ok=True)
    css = []
    for role, alias in (("display", "PF Display"), ("body", "PF Body"), ("mono", "PF Mono")):
        _, files, _ = fonts[role]
        for i, (path, weight, style) in enumerate(files):
            dst = out / f"{role}-{i}{path.suffix}"
            shutil.copy(path, dst)
            css.append(f'@font-face {{ font-family: "{alias}"; src: url("fonts/{dst.name}"); font-weight: {weight}; font-style: {style}; }}')
    return "<style>\n" + "\n".join(css) + "\n</style>"


# ---------------------------------------------------------------- resolve
DEFAULT_TYPE = {"weight": 700, "sub_weight": 500, "tracking": -0.03, "case": "none", "align": "center",
                "line_height": 1.06, "scale": 1.0}


def resolve(spec, base, palette_arg=None):
    """Return (style dict for the template, fonts dict, info lines)."""
    info = []
    if isinstance(spec, str) and spec.endswith(".json"):
        p = base / spec
        if not p.exists(): sys.exit(f"style file not found: {p}")
        spec = json.loads(p.read_text())
        base = p.parent          # font paths in style.json are relative to the style file
    if spec in (None, "launch") or (isinstance(spec, dict) and spec.get("preset") == "launch"):
        extra = spec if isinstance(spec, dict) else {}
        name, (deep, mid, light, text) = pick_palette(palette_arg or extra.get("palette", "auto"))
        info.append(f"style: launch preset, palette {name} (pin with --palette {name})")
        spec = {"preset": "launch", "_palette": name, "theme": "dark" if luminance(mid) < 0.3 else "light",
                "colors": {"bg": deep, "text": text, "accent": light}, "background": "launch",
                "launch": {"deep": deep, "mid": mid, "light": light}, "staging": "phone",
                "motion": "cinematic", "radius": 14, "shadow": "soft", "cta_style": "text",
                "fonts": {"display": "Inter", "body": "Inter", "mono": "JetBrains Mono"},
                "type": {"weight": 600, "tracking": -0.035}, **{k: v for k, v in extra.items() if k not in ("preset", "palette")}}
    st = json.loads(json.dumps(spec))
    st.pop("evidence", None)
    c = st.setdefault("colors", {})
    c.setdefault("bg", "#0b0b0d"); c.setdefault("text", on_color(c["bg"]))
    dark = luminance(c["bg"]) < 0.25
    st.setdefault("theme", "dark" if dark else "light")
    c.setdefault("accent", c["text"])
    c.setdefault("muted", mix(c["text"], c["bg"], 0.42))
    c.setdefault("surface", mix(c["bg"], c["text"], 0.06))
    c.setdefault("border", mix(c["bg"], c["text"], 0.16))
    c.setdefault("bg2", mix(c["bg"], c["accent"], 0.12))
    c["on_accent"] = c.get("on_accent") or on_color(c["accent"])
    if contrast(c["text"], c["bg"]) < 3:
        info.append(f"warning: text {c['text']} on bg {c['bg']} has low contrast ({contrast(c['text'], c['bg']):.1f}:1)")
    st.setdefault("motion", "cinematic")
    st.setdefault("staging", "panel")
    st.setdefault("background", "solid")
    st.setdefault("radius", 12); st.setdefault("shadow", "soft")
    st["type"] = {**DEFAULT_TYPE, **st.get("type", {})}
    st.setdefault("lens", LENS_BY_MOTION.get(st["motion"], 0.5))
    st.setdefault("sound_design", SFX_BY_MOTION.get(st["motion"], "soft"))
    fonts_spec = st.pop("fonts", {}) or {}
    fonts = {}
    for role in ("display", "body", "mono"):
        fspec = fonts_spec.get(role) or (fonts_spec.get("display") if role == "body" else None)
        fonts[role] = resolve_font(fspec, role, base)
        info.append(f"font {role}: {fonts[role][0]} ({fonts[role][2]})")
    info.append(f"look: {st['theme']} · motion {st['motion']} · staging {st['staging']} · background {st['background']} · lens {st['lens']}")
    return st, fonts, info
