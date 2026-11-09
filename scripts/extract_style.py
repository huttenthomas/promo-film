#!/usr/bin/env python3
"""Extract a project's visual identity into style.json for the promo film.

    python extract_style.py --url http://localhost:3000 --out style.json          # running app/site (best)
    python extract_style.py --static ./public --out style.json                    # static build folder
    python extract_style.py --project . --out style.json                          # no server: read CSS/Tailwind

Runtime mode loads the page in Chromium and reads *computed* styles: page background, text colours,
heading/body/mono fonts (and downloads their @font-face files), button and card radius, borders,
shadows, letter case and tracking, plus area-weighted colour usage. Static mode scans CSS, SCSS,
Tailwind config and theme files for custom properties, colours and fonts.

The output is a draft: `colors`, `fonts`, `type`, `radius`, `shadow`, ... plus an `evidence` block
(ranked colours, where each guess came from). Review it against a screenshot, then set `motion`,
`staging` and `background` to fit the project's personality.
"""
import argparse, collections, json, re, sys, urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from style import luminance, contrast, mix, GENERIC  # noqa: E402

COLLECT_JS = r"""
() => {
  const cs = e => getComputedStyle(e);
  const rgb2hex = s => { const m = String(s).match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); if (p.length > 3 && p[3] < 0.5) return null;
    return '#' + p.slice(0, 3).map(v => Math.round(v).toString(16).padStart(2, '0')).join(''); };
  const vis = e => { const r = e.getBoundingClientRect(); const s = cs(e);
    return r.width > 2 && r.height > 2 && s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0.3; };
  const area = e => { const r = e.getBoundingClientRect(); return Math.max(0, Math.min(r.right, innerWidth * 2) - Math.max(r.left, 0)) * Math.max(0, Math.min(r.bottom, innerHeight * 3) - Math.max(r.top, 0)); };
  let pageBg = null;
  for (const e of [document.body, document.documentElement]) { const c = rgb2hex(cs(e).backgroundColor); if (c) { pageBg = c; break; } }
  const bgArea = {}, textLen = {}, all = [...document.body.querySelectorAll('*')].filter(vis).slice(0, 4000);
  for (const e of all) {
    const s = cs(e), b = rgb2hex(s.backgroundColor);
    if (b) bgArea[b] = (bgArea[b] || 0) + area(e);
    const own = [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join('');
    if (own) { const c = rgb2hex(s.color); if (c) textLen[c] = (textLen[c] || 0) + own.length; }
  }
  const pick = (sel, n = 6) => [...document.querySelectorAll(sel)].filter(vis).slice(0, n);
  const desc = e => { const s = cs(e); return { tag: e.tagName.toLowerCase(), text: (e.innerText || '').trim().slice(0, 40),
    font: s.fontFamily, weight: s.fontWeight, size: parseFloat(s.fontSize), tracking: s.letterSpacing, transform: s.textTransform,
    lineHeight: s.lineHeight, color: rgb2hex(s.color), bg: rgb2hex(s.backgroundColor), radius: s.borderTopLeftRadius,
    border: s.borderTopWidth + ' ' + s.borderTopStyle + ' ' + (rgb2hex(s.borderTopColor) || ''), shadow: s.boxShadow }; };
  // the biggest visible headline sets the display type
  const headings = pick('h1, h2, h3, [class*=title i], [class*=heading i], [class*=hero i]', 30)
    .filter(e => (e.innerText || '').trim().length > 0).sort((a, b) => parseFloat(cs(b).fontSize) - parseFloat(cs(a).fontSize)).slice(0, 6);
  const buttons = pick('button, a[class*=btn i], a[class*=button i], [role=button], .btn, input[type=submit]', 12);
  const cards = all.filter(e => { const s = cs(e); return (s.boxShadow !== 'none' || parseFloat(s.borderTopWidth) > 0 || rgb2hex(s.backgroundColor))
    && parseFloat(s.borderTopLeftRadius) > 0 && area(e) > 4000; }).slice(0, 30);
  const body = cs(document.body);
  const mono = pick('code, pre, kbd, [class*=mono i]', 3);
  const links = pick('a', 20).map(a => rgb2hex(cs(a).color)).filter(Boolean);
  // @font-face rules we can read (same-origin sheets)
  const faces = [];
  // walk every readable sheet, including @import-ed and @media-nested ones
  const sheets = []; const walk = sh => { if (!sh || sheets.includes(sh)) return; sheets.push(sh); let rs; try { rs = sh.cssRules; } catch (e) { return; }
    for (const r of rs || []) { if (r.styleSheet) walk(r.styleSheet); } };
  for (const sh of document.styleSheets) walk(sh);
  for (const sh of sheets) { let rules; try { rules = sh.cssRules; } catch (e) { continue; }
    for (const r of rules || []) if (r.constructor.name === 'CSSFontFaceRule') {
      const fam = r.style.getPropertyValue('font-family').replace(/["']/g, '').trim();
      const src = r.style.getPropertyValue('src'); const urls = [...src.matchAll(/url\(["']?([^"')]+)["']?\)/g)].map(m => new URL(m[1], sh.href || location.href).href);
      faces.push({ family: fam, weight: r.style.getPropertyValue('font-weight') || '400', style: r.style.getPropertyValue('font-style') || 'normal', urls });
    } }
  // :root custom properties that look like colours
  const vars = {};
  for (const sh of sheets) { let rules; try { rules = sh.cssRules; } catch (e) { continue; }
    for (const r of rules || []) if (r.selectorText && /(^|,)\s*(:root|html|body|\.dark|\[data-theme)/.test(r.selectorText))
      for (const name of r.style) if (name.startsWith('--')) vars[name] = r.style.getPropertyValue(name).trim(); }
  const fontLinks = [...document.querySelectorAll('link[href*="fonts.googleapis"], link[href*="fonts.bunny"], link[href*="use.typekit"]')].map(l => l.href);
  const logo = [...document.querySelectorAll('header img, nav img, a[href="/"] img, [class*=logo i] img, img[class*=logo i], img[alt*=logo i], header svg, [class*=logo i] svg')]
    .filter(vis).slice(0, 3).map(e => e.tagName === 'IMG' ? { type: 'img', src: e.currentSrc || e.src } : { type: 'svg', svg: e.outerHTML.slice(0, 20000) });
  return { pageBg, bodyColor: rgb2hex(body.color), bodyFont: body.fontFamily, bgArea, textLen,
    headings: headings.map(desc), buttons: buttons.map(desc), cards: cards.map(desc), mono: mono.map(desc), links,
    faces, vars, fontLinks, logo, title: document.title };
}
"""


def first_family(stack):
    for f in (stack or "").split(","):
        f = f.strip().strip("\"'")
        if f and f.lower() not in GENERIC and not f.startswith("var("): return f
    return None


def saturation(h):
    import colorsys
    from style import _rgb
    r, g, b = _rgb(h); _, l, s = colorsys.rgb_to_hls(r, g, b)
    return s * (1 - abs(2 * l - 1))  # chroma-ish


def px(v):
    try: return float(str(v).replace("px", "").split()[0])
    except Exception: return None


def from_runtime(d, page_shot=None):
    ev = {"source": "runtime"}
    bg = d["pageBg"] or "#ffffff"
    bg_rank = sorted(d["bgArea"].items(), key=lambda kv: -kv[1])
    if bg_rank and (d["pageBg"] in (None, "#ffffff")) and bg_rank[0][1] > 0:
        # sites often paint the background on a wrapper rather than <body>
        bg = bg_rank[0][0] if bg_rank[0][1] > 1e6 else bg
    txt_rank = sorted(d["textLen"].items(), key=lambda kv: -kv[1])
    text = d["bodyColor"] or (txt_rank[0][0] if txt_rank else "#111111")
    heads = d["headings"]
    if heads and heads[0]["color"] and contrast(heads[0]["color"], bg) >= 3: text = heads[0]["color"]
    muted = next((c for c, _ in txt_rank if c != text and 2.2 <= contrast(c, bg) < contrast(text, bg)), None)
    # accent: the most-used saturated colour among buttons, links and backgrounds
    votes = collections.Counter()
    for b in d["buttons"]:
        if b["bg"] and saturation(b["bg"]) > 0.15: votes[b["bg"]] += 6
        if b["color"] and saturation(b["color"]) > 0.25: votes[b["color"]] += 2
    for c in d["links"]:
        if saturation(c) > 0.25: votes[c] += 1
    for c, a in bg_rank[:12]:
        if saturation(c) > 0.2 and c != bg: votes[c] += min(6, a / 50000)
    accent = votes.most_common(1)[0][0] if votes else text
    surface = next((c for c, a in bg_rank if c != bg and contrast(c, bg) < 1.6), None)
    radii = [px(x["radius"]) for x in d["buttons"] + d["cards"] if px(x["radius"])]
    rad = sorted(radii)[len(radii) // 2] if radii else 8
    shadows = [x["shadow"] for x in d["cards"] + d["buttons"] if x["shadow"] and x["shadow"] != "none"]
    shadow = "none"
    if shadows:
        s0 = shadows[0]
        nums = [float(n) for n in re.findall(r"(-?[\d.]+)px", s0)]
        shadow = "hard" if len(nums) >= 3 and nums[2] == 0 and (abs(nums[0]) + abs(nums[1])) > 0 else "soft"
    borders = [x["border"] for x in d["cards"] + d["buttons"] if x["border"] and not x["border"].startswith("0px") and "none" not in x["border"]]
    bw = px(borders[0]) if borders else 0
    bcol = borders[0].split()[-1] if borders and borders[0].split()[-1].startswith("#") else None
    h = heads[0] if heads else {}
    display = first_family(h.get("font")) or first_family(d["bodyFont"])
    body = first_family(d["bodyFont"])
    mono = first_family(d["mono"][0]["font"]) if d["mono"] else None
    tracking = 0.0
    if h.get("tracking") and h["tracking"] not in ("normal", "0px") and h.get("size"):
        tracking = round((px(h["tracking"]) or 0) / h["size"], 3)
    weight = int(h.get("weight") or 700)
    case = "upper" if h.get("transform") == "uppercase" else "none"
    btn_radius = px(d["buttons"][0]["radius"]) if d["buttons"] and px(d["buttons"][0]["radius"]) is not None else rad
    style = {
        "colors": {k: v for k, v in {"bg": bg, "text": text, "muted": muted, "accent": accent, "surface": surface,
                                     "border": bcol}.items() if v},
        "fonts": {"display": {"family": display}, "body": {"family": body}, **({"mono": {"family": mono}} if mono else {})},
        "type": {"weight": max(500, min(900, weight)), "tracking": max(-0.06, min(0.12, tracking - 0.01 if case == "none" else tracking)),
                 "case": case},
        "radius": rad, "button_radius": btn_radius, "shadow": shadow, "border_width": bw or 0,
        **({"border_color": bcol} if bcol else {}),
        "theme": "dark" if luminance(bg) < 0.25 else "light",
    }
    ev.update({"title": d.get("title"), "page_bg": d["pageBg"], "bg_by_area": bg_rank[:8], "text_by_length": txt_rank[:6],
               "accent_votes": votes.most_common(6), "headings": heads[:3], "buttons": d["buttons"][:4],
               "radii_seen": sorted(set(radii))[:12], "shadows_seen": shadows[:3], "css_vars": dict(list(d["vars"].items())[:40]),
               "font_links": d["fontLinks"], "faces": [{"family": f["family"], "weight": f["weight"]} for f in d["faces"]][:20],
               "logo_candidates": [l.get("src", "inline svg") for l in d["logo"]]})
    return style, ev


def download_faces(page, d, style, out_dir):
    """Download the @font-face files for the chosen families so the film uses the real fonts."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for role in ("display", "body", "mono"):
        f = style["fonts"].get(role)
        if not f: continue
        fam = f["family"]
        faces = [x for x in d["faces"] if x["family"].lower() == fam.lower()]
        files = []
        for fc in faces:
            url = next((u for u in fc["urls"] if u.endswith(".woff2")), None) or next((u for u in fc["urls"] if re.search(r"\.(woff|ttf|otf)(\?|$)", u)), None)
            if not url: continue
            name = re.sub(r"[^\w.-]", "_", Path(urllib.parse.urlparse(url).path).name)
            dst = out_dir / name
            if not dst.exists():
                try:
                    r = page.request.get(url)
                    if r.ok: dst.write_bytes(r.body())
                except Exception: continue
            if dst.exists():
                w = fc["weight"].split()[0] if fc["weight"] else "400"
                w = {"normal": "400", "bold": "700"}.get(w, w)
                files.append({"path": str(dst), "weight": int(float(w)), "style": fc["style"] or "normal"})
        if files: f["files"] = files


def from_static(root):
    """No server: scan stylesheets and theme config for colours, fonts and radii."""
    texts = []
    for p in root.rglob("*"):
        if any(x in p.parts for x in ("node_modules", ".git", "dist", "build", ".next", "vendor")): continue
        if p.suffix in (".css", ".scss", ".sass", ".less") or p.name.startswith(("tailwind.config", "theme.")) or p.name in ("globals.css",):
            try: texts.append(p.read_text(errors="ignore")[:300000])
            except Exception: pass
    blob = "\n".join(texts)
    colors = collections.Counter(c.lower() for c in re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", blob))
    vars_ = dict(re.findall(r"(--[\w-]+)\s*:\s*([^;}{]+);", blob))
    fams = collections.Counter(first_family(m) for m in re.findall(r"font-family\s*:\s*([^;}{]+)", blob))
    fams.pop(None, None)
    rad = collections.Counter(int(float(x)) for x in re.findall(r"border-radius\s*:\s*([\d.]+)px", blob))
    pick = lambda *names: next((vars_[n].strip() for n in names if n in vars_ and vars_[n].strip().startswith("#")), None)
    bg = pick("--background", "--bg", "--color-bg", "--color-background") or (colors.most_common(1)[0][0] if colors else "#ffffff")
    text = pick("--foreground", "--text", "--color-text", "--fg") or ("#111111" if luminance(bg) > 0.4 else "#f5f5f5")
    accent = pick("--primary", "--accent", "--brand", "--color-primary", "--color-accent")
    if not accent:
        sat = [(c, n) for c, n in colors.most_common(30) if saturation(c if len(c) == 7 else "#" + "".join(ch * 2 for ch in c[1:])) > 0.25]
        accent = sat[0][0] if sat else text
    fam = fams.most_common(1)[0][0] if fams else None
    style = {"colors": {"bg": bg, "text": text, "accent": accent}, "fonts": {"display": {"family": fam}, "body": {"family": fam}} if fam else {},
             "radius": rad.most_common(1)[0][0] if rad else 8, "theme": "dark" if luminance(bg) < 0.25 else "light"}
    ev = {"source": "static", "top_colors": colors.most_common(12), "css_vars": dict(list(vars_.items())[:40]),
          "font_families": fams.most_common(6), "radii": rad.most_common(6)}
    return style, ev


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--url"); g.add_argument("--static"); g.add_argument("--project")
    ap.add_argument("--path", default="/")
    ap.add_argument("--out", default="style.json")
    ap.add_argument("--fonts-dir", default=None, help="where to save downloaded font files (default: <out dir>/fonts)")
    ap.add_argument("--dark", action="store_true", help="read the dark theme (prefers-color-scheme: dark)")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    if a.project:
        style, ev = from_static(Path(a.project).resolve())
    else:
        from playwright.sync_api import sync_playwright
        httpd, url = None, a.url
        if a.static:
            from capture import serve
            httpd, base = serve(Path(a.static).resolve()); url = base + a.path
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            ctx = b.new_context(viewport={"width": 1440, "height": 900}, color_scheme="dark" if a.dark else "light")
            page = ctx.new_page(); page.goto(url, wait_until="networkidle"); page.wait_for_timeout(500)
            d = page.evaluate(COLLECT_JS)
            style, ev = from_runtime(d)
            download_faces(page, d, style, Path(a.fonts_dir) if a.fonts_dir else out.parent / "fonts")
            # save logo candidate if it's an image
            for i, lg in enumerate(d["logo"][:1]):
                try:
                    if lg["type"] == "img":
                        r = page.request.get(lg["src"]); ext = Path(urllib.parse.urlparse(lg["src"]).path).suffix or ".png"
                        if r.ok: (out.parent / f"logo{ext}").write_bytes(r.body()); ev["logo_saved"] = f"logo{ext}"
                    else:
                        (out.parent / "logo.svg").write_text(lg["svg"]); ev["logo_saved"] = "logo.svg"
                except Exception: pass
            b.close()
        if httpd: httpd.shutdown()
    # make font paths relative to the style file
    for f in style.get("fonts", {}).values():
        for x in f.get("files", []):
            try: x["path"] = str(Path(x["path"]).resolve().relative_to(out.parent))
            except ValueError: pass
    style.update({"motion": "TODO: cinematic | snappy | playful | calm", "staging": "TODO: panel | none | phone | browser",
                  "background": "TODO: solid | gradient | glow | grid | dots", "evidence": ev})
    out.write_text(json.dumps(style, indent=2))
    c = style["colors"]
    print(f"wrote {out}\n  bg {c.get('bg')}  text {c.get('text')}  accent {c.get('accent')}  muted {c.get('muted')}  surface {c.get('surface')}")
    print(f"  fonts: " + ", ".join(f"{k}={v.get('family')}{' (+files)' if v.get('files') else ''}" for k, v in style.get("fonts", {}).items()))
    print(f"  radius {style.get('radius')}  shadow {style.get('shadow')}  border {style.get('border_width')}  theme {style.get('theme')}")
    print("  -> review against a screenshot, then fill in motion / staging / background")


if __name__ == "__main__":
    main()
