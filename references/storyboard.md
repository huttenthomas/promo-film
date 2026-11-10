# Storyboard & style reference

## Contents
1. style.json
2. Storyboard top level
3. Scenes: shot · pieces · title · list · quote · end · stack · loop · carousel · collage
4. Roles and arcs
5. Transitions
6. Camera moves
7. Music & sound
8. Examples: product (own style) · person/portfolio · CLI · showcase · choreography · editorial
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
  "direction": "classic",         // classic | showcase | choreography | editorial (see SKILL.md)
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
| `backdrop` | `"disc"`: a soft disc in the project's surface/accent colour grows in behind the device (showcase look). `backdrop_at` = seconds |
| `screen2` | a second screen of the same app, standing just behind and right of the first (phone pairs). `screen2_at` = seconds |

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

### `stack`: one UI component performs (choreography)
```json
{ "type": "stack", "items": [
    { "title": "Order #4821 is late", "meta": "Email", "text": "Can you give me a new delivery date?" },
    { "title": "Refund request", "meta": "Chat", "text": "I was charged twice in March.", "icon": "screens/avatar.png" },
    { "crop": [0.16, 0.12, 0.62, 0.07] } ],
  "screen": "screens/inbox.png", "width": 0.42, "caption": { "text": "...", "side": "left" } }
```
Cards land one per beat at the bottom of a stack and push the earlier ones up; once the stack is taller
than `max_height` (fraction of the frame) the oldest scroll out the top. Text cards are drawn in the
project's style (surface, radius, border, shadow, accent initial as icon unless `icon` or `"icons": false`)
and their `text` types itself in. `crop` items are real fragments of `screen` (like `pieces`). Use the
project's real items — real notification wording, real ticket titles from a demo account — not invented
customers. 3–6 items; text ≤ 12 words; give it 0.55 s per card + 1 s.

### `loop`: endless image columns (editorial)
`{"type": "loop", "images": ["work/a.jpg", ...], "columns": 4, "title": "Identity.\nPrint. Motion.", "speed": 0.16}`
Columns scroll at constant speed in alternating directions; `title` sits over them (in `title_color`,
default the background colour with a soft shadow). `ratio` = tile height/width (1.25). 8+ images.

### `carousel`: one word per image (editorial)
`{"type": "carousel", "items": [{"image": "work/a.jpg", "word": "Brands"}, {"image": "work/b.jpg", "word": "people"}, ...]}`
A strip glides sideways; the image crossing the centre grows (`focus_scale`) and its word lights up, so the
words read as one sentence. `label: "over"` puts words on the images (only on dark/busy photos).
4–7 items, ~0.5 s per item.

### `collage`: burst of images around a title (editorial)
`{"type": "collage", "images": ["work/a.jpg", ...], "title": "Foldline", "size": "large"}`
Up to 10 images fly out from behind the title in quick succession (`stagger`, default 0.07 s) to a loose
scatter that keeps the title zone clear, then drift apart with depth. `slots: [[x, y, w], ...]` overrides
the layout; `rotate: false` for straight tiles.

### Any scene
`"invert": true` swaps background and ink for that scene (editorial cream ↔ black alternation);
`"bg": "#hex"` sets a scene background.

`*word*` in any text uses the highlight colour. Lines split on `\n`.
With `direction` showcase or choreography (or `style.reveal: "words"`), headlines and captions build word
by word: each word rises a little and arrives pale, then darkens to full ink.

## 4. Roles and arcs
Roles: `hook`, `reveal`, `benefit`, `proof`, `cta` (product/library/service) and `intro`, `service`, `work`,
`about`, `process` (person/service). The linter checks the arc for the `subject`. The music's lift lands
on the `reveal` scene — or, without one, on the first `work`/`service` scene. Major moments land on
downbeats; everything else on the beat.

## 5. Transitions (how a scene comes in)
`cut` (default, on the beat) · `slide` (whole frame slides up, crisp — snappy/playful) · `whip` (fast
horizontal with motion blur) · `blur` (defocus dissolve — cinematic/calm) · `dip` (through the background) ·
`zoom` (zoom-through: the old scene rushes at the camera and defocuses while the new one settles in —
choreography, showcase) · `wipe` (the new scene slides in from the left with a hard edge and covers the
old one — showcase, editorial).

## 6. Camera moves
Flat (any staging, the only ones for full-bleed): `drift`, `zoom-in`, `zoom-out`, `pan-down`, `pan-across`,
`push-in`, `rise` (panel enters from below with the style's bounce).
3D (panel, phone, browser): `tilt` (gentle, good for panels), `float`, `hero-turn`, `sweep`, `pull-back`,
`macro-drift`, `macro-rack`, `tilt-up`. Panels tilt only as much as `style.tilt` allows.
Device only (phone/browser/window): `spin` (rises from below while making a full turn, settles facing
camera — the showcase reveal; give it ≥ 2.5 s), `turntable` (slow half-turn for a held hero shot).
`punch` (any staging): a hard-cut close-up on `focus`, barely drifting — cut to it, hold 1.5–2 s, cut back.
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

### Showcase (mobile app, 15 s)
```json
{ "subject": "product", "direction": "showcase", "target_duration": 15, "style": "style.json", "music": "music/make-funk.mp3", "scenes": [
  { "type": "title", "role": "hook", "duration": 1.6, "text": "Surf the\n*right hour.*" },
  { "type": "shot", "role": "reveal", "duration": 3.0, "screen": "screens/home.png", "device": "phone", "move": "spin", "backdrop": "disc",
    "caption": { "text": "Tide, swell\nand wind.", "side": "left" } },
  { "type": "shot", "role": "benefit", "duration": 1.8, "transition": "wipe", "screen": "screens/home.png", "device": "phone", "move": "punch", "focus": [0.5, 0.2] },
  { "type": "shot", "role": "benefit", "duration": 2.4, "transition": "zoom", "screen": "screens/detail.png", "device": "phone", "move": "turntable", "backdrop": "disc",
    "caption": { "text": "Best spots,\n*ranked.*", "side": "right" } },
  { "type": "shot", "role": "benefit", "duration": 2.2, "transition": "slide", "screen": "screens/home.png", "screen2": "screens/detail.png", "device": "phone", "move": "float", "backdrop": "disc",
    "caption": { "text": "Plan the\n*dawn session.*", "side": "left" } },
  { "type": "end", "role": "cta", "duration": 4.0, "name": "Tidewise", "logo": "screens/logo.png", "tagline": "Tides for surfers.", "cta": "Get the app" } ] }
```

### Choreography (SaaS inbox, 15 s)
```json
{ "subject": "product", "direction": "choreography", "target_duration": 15, "style": "style.json", "music": "music/make-funk.mp3", "scenes": [
  { "type": "title", "role": "hook", "duration": 1.8, "text": "Every customer.\n*One inbox.*" },
  { "type": "stack", "role": "reveal", "duration": 4.0, "items": [ "... 4-5 real items from the demo account ..." ] },
  { "type": "shot", "role": "benefit", "duration": 2.0, "transition": "zoom", "screen": "screens/inbox.png", "device": "panel", "move": "punch", "focus": [0.42, 0.16] },
  { "type": "shot", "role": "benefit", "duration": 2.4, "screen": "screens/inbox.png", "device": "panel", "move": "tilt",
    "caption": { "text": "Sorted before\n*you open it.*", "side": "left" } },
  { "type": "end", "role": "cta", "duration": 4.8, "transition": "zoom", "name": "Relay", "tagline": "The shared inbox for small teams.", "cta": "Start free" } ] }
```

### Editorial (studio, 15 s)
```json
{ "subject": "service", "direction": "editorial", "target_duration": 15, "style": "style.json", "music": "music/make-funk.mp3", "scenes": [
  { "type": "collage", "role": "hook", "duration": 2.2, "images": ["work/01.jpg", "... 10 ..."], "title": "Foldline", "size": "large" },
  { "type": "loop", "role": "reveal", "duration": 2.6, "invert": true, "images": ["... 12 ..."], "title": "Identity.\nPrint. Motion." },
  { "type": "carousel", "role": "work", "duration": 3.4, "transition": "wipe", "items": [{ "image": "work/03.jpg", "word": "Brands" }, "... one word each ..."] },
  { "type": "list", "role": "service", "duration": 2.8, "invert": true, "items": ["Identity", "Packaging", "Motion"], "numbered": true },
  { "type": "end", "role": "cta", "duration": 4.0, "name": "Foldline", "tagline": "Design studio, Rotterdam.", "cta": "Start a project", "url": "foldline.studio" } ] }
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
- Editorial title unreadable over an image → `title_color`, fewer `images`, or custom `slots` clear of it.
- Stack text still typing at the cut → shorter `text`, fewer items, or more `duration`.
- Spin ends too late → give the `spin` shot ≥ 2.5 s, or use `hero-turn`.
