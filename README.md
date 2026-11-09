# promo-film

An agent skill that turns a project directory into a **short promo film in the project's own visual
identity and voice**: 15 seconds and snappy by default, 30 seconds on request. It extracts the colours,
fonts, corner radii, shadows and personality from the running site or app, and writes the captions in the
project's own words. It tells a short story (what the viewer gets, or who you are and what you do), shows
the real UI or work, and is cut on the beat to a CC0 hip-hop/funk track.

Works for **products and apps**, **open-source libraries and CLIs**, **personal portfolios** and
**freelancers/agencies**.

<!-- Add a GIF or a link to a sample render here -->

## What it does

1. **Understands the subject**: reads the README, manifests and pages, and decides whether it's a
   product, a library, a person or a service. Each gets its own story arc.
2. **Extracts the look** (`scripts/extract_style.py`): computed colours, heading/body/mono fonts (with the
   real font files), radii, borders, shadows, letter case and tracking from the live page. Claude reviews
   it and chooses the motion personality (cinematic, snappy, playful, calm), the staging and the background.
3. **Captures the visuals** (`scripts/capture.py`): crisp 2×/3× screenshots of the states that prove the
   story, plus cut-out UI pieces (buttons, cards, portfolio thumbnails).
4. **Captures the voice** (`voice.md`): collects real lines from the site, app or README, then matches their
   language, form of address, register and punctuation, so the captions sound like the project wrote them.
5. **Writes the story**: a brief, then a storyboard of fast cuts: scenes of 1.5–2 s, captions of 2–4 words,
   shots, floating UI pieces, titles, service lists, and an end card with the project's own button as the
   call to action. Only true claims and real quotes from the project.
6. **Cuts to music** (`scripts/music.py`, `scripts/sfx.py`): edits a CC0 track to the target length (real
   opening and ending), snaps cuts and type to the beat, adds sound design. The default is "Make Funk" by
   HoliznaCC0, downloaded when the film is made.
7. **Renders deterministically** (`scripts/render.py`): HTML/CSS driven frame by frame in headless Chromium.
   Flat looks render in about a minute; 3D device shots take longer.

There's also a `launch` preset: a dark, cinematic launch-film look on a 3D phone.

## Install

**Claude Code**
```bash
git clone https://github.com/huttenthomas/promo-film ~/.claude/skills/promo-film
pip install playwright librosa numpy && playwright install chromium   # plus ffmpeg
```
**Claude apps (claude.ai / desktop)**: zip this folder and upload it under *Settings → Capabilities → Skills*.

Then ask something like:
> Make a promo video for the project in `~/code/acme`.

> Make a 30-second version with a customer quote.

> Make a video for my portfolio site to post on LinkedIn, vertical.

> Make a teaser for this repo in the launch style.

## Run it by hand

```bash
python scripts/render.py examples/cli-demo.json --check            # lint
python scripts/render.py examples/cli-demo.json --stills sheet.png # contact sheet
python scripts/render.py examples/cli-demo.json --out demo.mp4     # full render (~4 min on 4 cores)
```
The bundled example is a 30-second cut. Set `"target_duration"` in the storyboard to change the length.

Flags: `--palette` (launch style), `--format landscape|square|vertical`, `--music none|auto|track.mp3`,
`--lens 0..1`, `--fps`, `--workers N`.

See [`references/storyboard.md`](references/storyboard.md) for the storyboard schema, the camera moves and
the shot templates.

## Requirements
- Python 3.9+, `playwright` with Chromium, `ffmpeg` (with libx264), `numpy`, `librosa`

## Notes & limits
- Flat stagings (panel, full-bleed, pieces) render in about a minute; 3D device shots take ~0.7 s per frame per worker
  (`--workers` parallelises). Iterate with `--stills`, render the MP4 once.
- Fonts: the project's own font files when the site serves them, otherwise Google Fonts via Fontsource,
  otherwise Inter.
- Music: films use a CC0 hip-hop/funk beat by default, which needs a network connection to download. For
  other moods, five CC0 tracks from [FreePD](https://freepd.com) are bundled (`assets/music/`) and ~15 more
  can be fetched on demand (`python scripts/music.py list`). CC0 means commercial use with no attribution
  required. You can also pass your own licensed track.
- Devices are generic on purpose (punch-hole phone, neutral window). This project is not affiliated with
  or endorsed by Apple. Don't add Apple trademarks to your films.

## License
Code: MIT (see `LICENSE`). Bundled fonts: Inter / Inter Display and JetBrains Mono, both under the SIL Open
Font License 1.1 (see `assets/fonts/*-OFL.txt`). Bundled music: CC0 1.0 (see `assets/music/LICENSE.md`).
