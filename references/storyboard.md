# Storyboard & style reference

## Contents
1. style.json
2. Storyboard top level
3. Scenes: shot · pieces · title · list · quote · end
4. Roles and arcs
5. Transitions
6. Camera moves
7. Music & sound
8. Examples: product (own style) · person/portfolio · CLI
9. Tuning tips

## 1. style.json
```jsonc
{
  "colors": { "bg": "#faf8ef", "text": "#776e65", "muted": "#a39a90", "accent": "#8f7a66",
              "highlight": "#f67c5f", "surface": "#eee4da", "border": "#d8cfc4" },
  "fonts":  { "display": "Clear Sans",                      // family name: fetched from Fontsource if needed
              "body": { "family": "Lato" },
              "mono": { "family": "Fira Code", "files": [{ "path": "fonts/fira.woff2", "weight": 400 }] } },
  "type":   { "weight": 700, "sub_weight": 500, "tracking": -0.02, "case": "none", "align": "left",
              "line_height": 1.06, "scale": 1.0 },
  "radius": 6, "button_radius": 3,              // CSS px as on the site
  "shadow": "soft", "shadow_color": "rgba(119,110,101,.22)",   // none | soft | hard | glow
  "border_width": 0, "border_color": "#000",
  "motion": "playful",                          // cinematic | snappy | playful | calm
  "staging": "panel",                           // panel | none | phone | browser
  "background": "solid",                        // solid | gradient | glow | grid | dots
  "lens": 0,                                    // optional; grain/bloom (defaults by motion: cinematic 1, calm .45, else 0)
  "tilt": 0.6,                                  // optional; how much panels rotate in 3D moves (0 = flat)
  "cta_style": "button"                         // button (accent-coloured, project radius) | text
}
```
Only `colors.bg` is required; the rest is derived. Font paths are relative to style.json.
Preset: `"style": "launch"` (dark cinematic phone look, rotating palette; `--palette` to pin one).

## 2. Storyboard top level
```jsonc
{ "subject": "product",          // product | library | person | service
  "target_duration": 30, "format": "landscape",   // landscape | square | vertical
  "style": "style.json",
  "music": "auto", "music_mood": null, "sound_design": true, "default_transition": "cut",
  "scenes": [ ... ] }
```

## 3. Scenes

### `shot`: a screen on camera
| key | meaning |
|---|---|
| `screen` | image path (screenshot, case-study image, photo). Or `terminal`: `{"lines": [{"cmd": ".."}, {"out": ".."}]}` |
| `device` | `panel` · `none` (full-bleed) · `phone` · `browser` · `window` (default: style.staging) |
| `dpr` | pixel ratio of the capture (phone captures 3, browser 2) so radii match the site |
| `move`, `focus`, `dir`, `intensity`, `scroll`, `camera` | see 6. `scroll: [from, to]` travels down tall pages |
| `caption` | `{"text": "Find anything\nin a *second.*", "sub": "...", "side": "left"\|"right"\|"over"}` |
| `url` / `title` | browser URL pill / window title |
| `full_height` | show a tall page whole instead of a window onto it |

### `pieces`: real UI fragments as floating cards
```json
{ "type": "pieces", "screen": "screens/full.png", "dpr": 2,
  "items": [ { "crop": [0.056, 0.275, 0.277, 0.086], "at": [0.22, 0.31], "width": 0.25, "rotate": 0, "from": "below" } ],
  "caption": { "text": "...", "side": "left" } }
```
`crop` = `[x, y, w, h]` fractions of the screen; `at` = centre in the frame (fractions); `width` = on-screen
width as a fraction of the frame; `from` = below | above | left | right; `rotate` in degrees. Items enter on
successive beats with the style's motion. Great for portfolio grids, buttons, stat cards, tiles, testimonials.

### `title`
`{"type": "title", "text": "Five minutes\nto spare?", "subtitle": "...", "eyebrow": "...", "size": "large"}`

### `list`: services, skills, steps
`{"type": "list", "title": "What I do", "items": ["Brand identity", "Web design", "Motion"], "numbered": true}`
2–6 items, ≤ 5 words each; each lands on a beat and earlier ones dim.

### `quote`: a real testimonial
`{"type": "quote", "text": "...", "author": "Jane Doe", "role": "CTO, Acme", "source": "site /testimonials"}`
Copy it exactly from the project. Never write one.

### `end`
`{"type": "end", "name": "Acme", "logo": "logo.svg", "tagline": "...", "cta": "Book a call", "url": "acme.dev"}`
The CTA renders as the project's own button (accent colour, button radius) unless `cta_style: "text"`.

`*word*` in any text uses the highlight colour. Lines split on `\n`.

## 4. Roles and arcs
Roles: `hook`, `reveal`, `benefit`, `proof`, `cta` (product/library/service) and `intro`, `service`, `work`,
`about`, `process` (person/service). The linter checks the arc for the `subject`. The music's lift lands
on the `reveal` scene — or, without one, on the first `work`/`service` scene. Major moments land on
downbeats; everything else on the beat.

## 5. Transitions (how a scene comes in)
`cut` (default, on the beat) · `slide` (whole frame slides up, crisp — snappy/playful) · `whip` (fast
horizontal with motion blur) · `blur` (defocus dissolve — cinematic/calm) · `dip` (through the background).

## 6. Camera moves
Flat (any staging, the only ones for full-bleed): `drift`, `zoom-in`, `zoom-out`, `pan-down`, `pan-across`,
`push-in`, `rise` (panel enters from below with the style's bounce).
3D (panel, phone, browser): `tilt` (gentle, good for panels), `float`, `hero-turn`, `sweep`, `pull-back`,
`macro-drift`, `macro-rack`, `tilt-up`. Panels tilt only as much as `style.tilt` allows.
`focus` = `[x, y]` fractions of the screen; `dir: -1` mirrors; `intensity` scales.

## 7. Music & sound
`python scripts/music.py list` — CC0 tracks (bundled + fetchable). `auto` picks by motion: cinematic →
inspiring, snappy → driving, playful → upbeat, calm → calm. The editor keeps the track's real opening and
ending and places its lift on the reveal. Sound design follows the motion: full (cinematic), soft
(playful, calm), whooshes only (snappy).

## 8. Examples

### Product in its own style (2048: playful, panel, left-aligned)
```json
{ "subject": "product", "style": "style.json", "music": "auto", "scenes": [
  { "type": "title", "role": "hook", "duration": 2.5, "text": "Five minutes\nto spare?" },
  { "type": "pieces", "role": "hook", "duration": 3, "screen": "screens/play.png", "dpr": 3,
    "items": [ { "crop": [0.338, 0.192, 0.149, 0.069], "at": [0.3, 0.42], "rotate": -8, "width": 0.15 } ] },
  { "type": "title", "role": "reveal", "duration": 2.5, "text": "2048", "size": "large", "subtitle": "Join the numbers." },
  { "type": "shot", "role": "benefit", "duration": 4, "transition": "slide", "device": "panel", "screen": "screens/play.png",
    "move": "tilt", "caption": { "text": "Learn it\nin *one swipe.*", "side": "left" } },
  { "type": "end", "role": "cta", "duration": 4.5, "name": "2048", "cta": "Play free", "url": "..." } ] }
```

### Person / portfolio (snappy, uppercase, brand colour background)
```json
{ "subject": "person", "style": "style.json", "music": "auto", "scenes": [
  { "type": "shot", "role": "intro", "duration": 3, "device": "none", "screen": "screens/hero.png", "move": "zoom-out", "focus": [0.5, 0.38] },
  { "type": "title", "role": "intro", "duration": 2.5, "text": "Sam Rivera", "size": "large", "subtitle": "Illustrator and web designer." },
  { "type": "list", "role": "service", "duration": 3.5, "transition": "slide", "title": "What I do", "numbered": true,
    "items": ["Brand illustration", "Web design", "Editorial art"] },
  { "type": "pieces", "role": "work", "duration": 4, "screen": "screens/full.png", "dpr": 2, "items": [ "... six portfolio thumbnails ..." ] },
  { "type": "shot", "role": "work", "duration": 4.5, "device": "panel", "screen": "screens/case-study.png", "move": "drift",
    "scroll": [0, 0.3], "caption": { "text": "Illustration\npeople *remember.*", "side": "left" } },
  { "type": "quote", "role": "about", "duration": 4, "text": "(exact words from the site)", "author": "(name)", "source": "/about" },
  { "type": "end", "role": "cta", "duration": 4.5, "name": "Sam Rivera", "tagline": "Illustrator · Web designer", "cta": "Get in touch", "url": "samrivera.design" } ] }
```

### CLI / library
See `examples/cli-demo.json` (terminal shots; `"style": "launch"` there — swap in the project's style.json).

## 9. Tuning tips
- Film looks generic → the style is off: compare the stills with the site and fix `colors`, `type.case`,
  `radius`, `shadow`, fonts. That's the most common problem.
- Panel too small/too big → `intensity`, or a different `device`; tall pages are windowed — use `scroll`.
- Pieces overlap → adjust `at`/`width`; keep 3–6 items.
- Text low-contrast warning → choose a darker/lighter `text`, or accept it if it's the brand's own big-type look.
- Busy → fewer pieces, longer shots, `calm` motion.
