---
name: "promo-film"
description: "Make a short promo video (MP4, 15 s snappy cut by default, 30 s on request) from a project or website, in that project's own visual identity and voice, cut to a CC0 hip-hop/funk beat. Use for promos, launch videos, teasers, trailers, showreels, product, portfolio or social videos."
---

# Promo film

Turn a project directory into a short, snappy film (default **15 s**; 20–30 s only when asked) that looks
like it was made by the project's own designer: the same colours, type, radii and feel as the site or app,
telling a short story about what the viewer gets, cut fast to music.

Every film follows one **direction** — its genre of motion — picked from what the project is (step 1b).
You write two small JSON files — **style.json** (the look, extracted from the project) and
**storyboard.json** (the story: scenes, captions, shots) — and run `scripts/render.py`. The renderer does
the craft: edits a CC0 track to exactly `target_duration`, snaps cuts to the beat, lands each line of type on a beat,
adds sound design, and renders deterministically through headless Chromium.

Requirements: `python3`, `playwright` + Chromium (`pip install playwright && playwright install chromium`),
`ffmpeg`, `numpy`, `librosa`. Check first; install what's missing.

## 1. Understand the subject
```bash
python <skill>/scripts/scan_project.py <project_dir> > facts.json
```
Read the README and the main pages. Decide the **subject** — it changes the whole story:

| subject | what it is | the viewer wants to know |
|---|---|---|
| `product` | an app, SaaS, game, tool | what do I get from it? |
| `library` | open-source package, CLI, API | will it make my work easier? |
| `person` | a portfolio or personal site | who is this, what do they do, is their work good, how do I hire them? |
| `service` | a freelancer/agency/studio offering | what problem do they solve, proof they can, how to start? |

Then write the brief (in your reply or a scratch file) — every scene will serve one line. For the default
15 s cut you will only use the promise, two points, one proof and the CTA, so pick the strongest:
- **Audience** — who should care, specifically.
- **Tension** (product/library/service) — the friction they know. For a person: the need they hire for.
- **Promise** — what changes for them, in one line.
- **Three points** — product/library: *outcomes* ("Find any note in a second"), not features.
  Person/service: services offered + the best 2–3 pieces of work.
- **Proof** — something true from the project: real numbers, years, clients named on the site, a real
  testimonial *as written on the site*. Never invent one. If there's none, skip proof.
- **Call to action** — the exact next step ("Book a call", "Try it free at …", "brew install …").

### Capture the voice (voice.md)
The captions must sound like the source wrote them, the same way the film looks like the source designed
it. Before writing any copy, collect the project's own words and write `film/voice.md`.

**Where to look** (in this order; the copy a visitor actually reads outweighs internal docs):
1. Hero headline + subline, button/CTA labels, nav labels on the live site or app.
2. Feature/services sections, about page, pricing page, empty states and microcopy in the UI.
3. README intro, package description, app-store text, `product-context.md` if the project has one.
4. Social bios or taglines only if they're in the repo.
Copy 8–15 real lines verbatim into `voice.md` as samples, with where each came from.

**Then describe the voice** from those samples, not from guesses about the industry:
- **Language & locale** — write captions in the language the source speaks to its audience (a Dutch site
  gets Dutch captions, even if this conversation is in English). Bilingual site: use the primary one, ask
  if unclear. Keep their spelling conventions (UK/US, Flemish/Dutch).
- **Address** — how the reader is addressed: you / we / I / third person; for Dutch/German/French also
  formal vs informal (u vs je, Sie vs du, vous vs tu). Never switch.
- **Register** — formal, plain, casual, technical, cheeky, poetic. One or two words.
- **Sentence shape** — typical length, fragments vs full sentences, questions, imperatives, sentence case
  vs Title Case, punctuation habits (full stops on headlines, ellipses, em dashes, `!`).
- **Vocabulary** — the project's own recurring words and names for things (what they call users,
  features, the product itself), jargon they use or avoid, humour or wordplay they do.
- **Not like this** — 2–3 traits that would sound wrong for this brand (e.g. "no hype", "no jokes",
  "never corporate").

The voice also informs the film's other choices: a dry, terse voice fits `snappy`/`calm` motion and a
restrained track; a playful voice fits `playful`. If the look and the voice pull different ways, follow
the look for visuals and the voice for copy, and mention it in the delivery note.

If the source has almost no copy (a bare repo, a one-line README), say so, base the voice on what little
there is plus the visual personality, and keep captions plain and neutral rather than inventing a
personality.

## 1b. Pick one direction
A direction is the film's genre: how things move, how fast, what the hero is. Pick exactly **one** per
film — mixing them reads as a template sampler. If the user asked for a look ("like an app store
trailer", "editorial", "show the notifications coming in"), that wins. Otherwise decide from the project:

| direction | pick it when | the hero | how it moves |
|---|---|---|---|
| `showcase` | a **mobile app** with good phone screens | the device | light and airy; the phone rises and makes a full turn while the headline builds word by word, settles before a soft disc, close-ups on the screen, pairs of phones. Long ease-outs (~2.5 s of motion, then ~1 s of stillness). |
| `choreography` | a product whose value lives in **one repeating UI element**: messages, notifications, tickets, tasks, search results, AI answers, transactions | that component | minimal backdrop; cards land one per beat and push up, their text types in, zoom-throughs between scenes, a hard punch-in on one detail. Calm and precise: ~0.7 s per entrance, 1–1.5 s holds. |
| `editorial` | **image-led** work — portfolio, photographer, studio, fashion/food/interior brand — with **10+ strong images** | the images | magazine-like; images burst around a big title, endless image columns, a carousel that spells a sentence one word per image, cream ↔ black scene alternation. Fast: a cut every ~2 s, quick eased bursts over constant gliding. |
| `classic` | everything else: libraries/CLIs, web apps without one hero component, text-led sites, too few images for editorial | screens and type | the default kit below (panels, pieces, camera moves, beat-cut type). |

Tie-breaks: a web SaaS with an inbox/feed → `choreography`, not `showcase`. A portfolio with only 4–5
projects → `classic` with `pieces` (editorial would look empty). A mobile app whose value is its feed →
`showcase`, and use a `stack` scene once for the feed. In the brief, state the direction and the one
reason for it ("showcase — it's an iOS/Android app and the screens are its best material").

Set it as `"direction": "..."` in the storyboard; the renderer retunes timing and type reveal to it and
the linter checks it has what it needs. Direction recipes (15 s):
- **showcase** — hook title (1.6 s) → `spin` reveal with `backdrop: "disc"` and a caption (3 s) →
  `wipe` to a `punch` close-up on the screen's best part (1.8 s) → `zoom` to a `turntable` of another
  screen (2.4 s) → phone pair with `screen2` (2.2 s) → end card (4 s). Staging `phone`; light `solid` bg.
- **choreography** — hook title (1.8 s) → `stack` of 4–5 of the product's real items (3.5–4 s) →
  `zoom` to a `punch` on the one detail that matters (2 s) → panel shot with caption (2.4 s) → `zoom`
  to end card (4.8 s). Staging `panel`, `gradient` or `solid` bg. Scenes may run 2–4 s here: the
  stillness between entrances is the look.
- **editorial** — `collage` with the name (2.2 s) → `loop` with services or a line, `invert` (2.6 s) →
  `wipe` to a `carousel` whose words form one sentence (3.4 s) → `list` or proof, `invert` (2.8 s) →
  end card with `cta_style: "text"` (4 s). Staging `none`, radius as the site, `snappy`.
Full examples are in `references/storyboard.md`.

## 2. Capture the look (style.json)
The film must look like the project, not like a template. Run the app or site (or serve its build folder)
and extract its identity:
```bash
python <skill>/scripts/extract_style.py --url http://localhost:3000 --out film/style.json
python <skill>/scripts/extract_style.py --static ./dist --out film/style.json        # static build
python <skill>/scripts/extract_style.py --project . --out film/style.json             # no way to run it
```
It reads computed colours, heading/body/mono fonts (downloading the real font files when it can), radii,
borders, shadows, letter case and tracking, and saves a logo candidate. **Then review it** against a
screenshot of the site — the extractor guesses, you decide:
- `colors.bg` should be the colour that *defines* the brand (a white site with a teal hero may want teal);
  `text` must read on it; `accent` is the brand's action colour (buttons); `highlight` (optional) is the
  colour for `*emphasised*` words; `surface` is the card colour.
- `fonts.display/body/mono`: family names; Google fonts are fetched automatically, project files are used
  when listed. If a font can't be found the renderer says so and falls back to Inter.
- `type`: `weight`, `tracking` (em), `case` ("upper" if headings are uppercase), `align` ("left" or "center").
- `radius`, `shadow` (`none` | `soft` | `hard` for neo-brutalist offset shadows | `glow`), `border_width`.
- **Set these three by judgement** — they're the personality:
  - `motion`: **default `snappy`** — it is what makes the films feel alive. Use `calm`/`cinematic` only
    when the user asks for a slower, premium feel; even then keep scenes short. Options: `cinematic` (slow, blurred reveals, film grain — premium/serious brands) · `snappy` (fast,
    crisp, hard cuts — dev tools, SaaS) · `playful` (pops and overshoot — games, consumer, friendly
    brands) · `calm` (long fades — wellness, editorial, luxury).
  - `staging` (default way to show screens): `panel` (a flat card with the project's radius/shadow — the
    default for most web projects) · `none` (full-bleed: the UI fills the frame) · `phone` (only when it's
    a mobile app) · `browser` (a window frame).
  - `background`: `solid` (most brands) · `gradient` · `glow` · `grid` · `dots` — pick what the site
    itself uses.
`"style": "launch"` is a separate preset: the dark cinematic launch-film look on a 3D phone with a rotating
palette. Use it only when the user asks for that look.

## 3. Get the visuals
Screens prove the story; for people and services, the *work* is the hero.
```bash
python <skill>/scripts/capture.py --url http://localhost:3000 --device browser --out film/screens/home.png
python <skill>/scripts/capture.py --static ./dist --device browser --full-page --out film/screens/full.png
python <skill>/scripts/capture.py --url ... --device phone --click "text=Pricing" --out film/screens/pricing.png
```
- Capture states that *show* each point (filled data, results, open panels). Empty states make dead shots.
- Portfolios: capture the work grid and individual case studies; project images/photos in the repo can be
  used directly as `screen` images (a headshot on the person's own site is fine — it's their material).
- **Per direction**: showcase needs 2–3 phone captures at 3x of the strongest screens; choreography
  needs the hero component with real content (log into the demo/seed data; note 4–6 real items' titles
  and text for the `stack`); editorial needs the actual work images from the repo (`public/`, `assets/`,
  case-study folders) — 10–14 of the best, varied in colour and framing.
- **Pieces**: for cut-out shots, open the screenshot, overlay a grid if needed
  (`ffmpeg -i s.png -vf "scale=600:-1,drawgrid=w=60:h=60:c=red@0.5" g.png`) and note crops as
  `[x, y, w, h]` fractions — buttons, cards, tiles, portfolio thumbnails, a stat, a testimonial card.
- CLIs: `terminal` shots with real commands and output.

## 4. Write the storyboard
Read `references/storyboard.md`: scene types (`shot`, `pieces`, `title`, `list`, `quote`, `end`), moves,
transitions, the arcs per subject, and examples.

### Pacing — this matters more than length
A film feels snappy because of how often it cuts and how little there is to read, not because it is short.
- Set `"target_duration": 15` by default.
- **Scenes 1.5–2 s**; only the end card holds longer (4–4.5 s). Never more than 2.5 s for a mid-film scene
  — except the direction's signature scene: a `spin` (≤ 3 s), a `stack` (≤ 4 s), a `carousel` (≤ 3.5 s).
- **Captions and titles 2–4 words.** A viewer must read it in one beat. Long lines force long scenes.
- **One idea per cut.** Split a busy scene into two quick ones rather than holding one longer.
- Transitions `cut` / `whip` / `slide` only. No `dip`/`blur` in the snappy cut.
- Use the default hip-hop/funk beat (see Music below), not `"music": "auto"`.
- Long testimonials don't fit a 15 s cut; use a short stat as proof instead (e.g. a rating, a customer count).
  Never trim words out of the middle of a quote to make it fit — use it whole or not at all.

Default 15 s arc for `classic` (product/library; other directions: see 1b): reveal with their own hero line (2 s) → stat or benefit (1.5 s) →
benefit + visual (2 s) → benefit + visual (2 s) → proof stat (1.5 s) → payoff line (1.5 s) → cta (4.5 s).

Longer arcs, for a 30 s version on request:

- **product / library**: hook → reveal (name, on the music's lift) → 3 × benefit (caption + proof shot)
  → proof → payoff → cta
- **person**: intro (who + what, often over their own hero/avatar) → services (`list`) → work (2–3 scenes:
  `pieces` grid, panels/full-bleed of case studies) → proof/about (`quote` or fact) → cta ("Get in touch")
- **service**: hook (client's problem) → reveal (studio name) → services (`list`) → work/results → process
  or `quote` → cta ("Book a call")

Writing rules, and why:
- **Speak to the viewer's outcome**, short and concrete. Captions 2–4 words in the 15 s cut (≤ 7 in a
  30 s cut), list items ≤ 3 words.
- **Write in the source's voice (voice.md), not a model's.** Same language, same form of address, same
  register, same sentence shape and punctuation habits. Reuse the project's own words and phrases
  wherever they fit — a real tagline or hero line from the site usually beats a new one, especially for
  the reveal and the CTA (use their actual button label). After drafting, read every caption next to the
  samples in voice.md: if a line would look out of place on their own site, rewrite it.
- **No generic hype.** Don't introduce: unleash, supercharge, elevate, seamless, revolutionize,
  next-gen, game-changer, empower, unlock, effortless, "passionate about", "crafting digital
  experiences", "the future of", or their equivalents in other languages. The one exception: if the
  source itself uses such a word or `!`/emoji as a consistent part of its voice, you may use it the way
  they do — note this in voice.md so the linter's flag is a known, deliberate choice. The linter only
  checks English words; for other languages, check by hand.
- **Show what you say** — every caption sits on a visual that proves it.
- **Vary rhythm and staging**: mix `pieces`, `shot` and type scenes; don't repeat a move back to back.
- **Match the motion personality** in transitions: snappy → `cut`/`slide`/`whip`; cinematic → `cut`/`blur`;
  playful → `slide`/`cut`; calm → `blur`/`dip`.
- **Renderer gotchas:** `*emphasis*` can't span a line break (close it before `\n`). With a caption on the
  side, `pieces` are shifted right by the caption width, so place items around x 0.5–0.55 to land at
  ~0.68. Piece backgrounds use `colors.surface`, so for transparent cut-outs set `surface` to the bg colour.
  The `quote` scene prints `role` as the job title but the linter requires a story role, so show a quote as a
  `title` scene with the attribution in `subtitle`.

### Music — default: a hip-hop/funk beat
Every render uses a beat-driven hip-hop/funk track unless the user asks for something else. The
reference sound is "Make Funk" by HoliznaCC0: ~99 bpm, drums carry the track, the beat is in within
~2 s, no long intro, no vocals. Use it by default:
```bash
mkdir -p film/music && curl -sL -o film/music/make-funk.mp3 \
  "https://raw.githubusercontent.com/SoundSafari/CC0-1.0-Music/main/freemusicarchive.org/HoliznaCC0%20-%20Make%20Funk.mp3"
```
then `"music": "music/make-funk.mp3"` in the storyboard. HoliznaCC0 releases everything on the Free
Music Archive under CC0 1.0, so no attribution is required.

When several films are made side by side and the user wants them to differ, pick another track that
matches the reference instead of reusing it. Candidates are in the same CC0 mirror (list with
`git clone --filter=blob:none --no-checkout https://github.com/SoundSafari/CC0-1.0-Music` then
`git ls-tree -r --name-only HEAD | grep -i holiznacc0`). Accept a track only if it measures close to the
reference with librosa:
- tempo 90–105 bpm (`librosa.beat.beat_track`)
- percussive share ≥ 0.2 of the energy (`librosa.effects.hpss`; "Make Funk" measures ~0.27)
- loud within the first 2–3 s (RMS above about −20 dB by second 2)
Slower, melodic HoliznaCC0 beats such as "Good Vibes", "City Lights" and "Broken Hustle" (83–89 bpm,
percussive share 0.06–0.14, some with quiet intros) don't match. Tell the user which track you used and
that you chose it by measurement, since you can't listen to it.

Other options only on request: `"music": "auto"` with `music_mood` (inspiring | upbeat | calm |
driving), `"library:<title>"`, or the user's own licensed file.

## 5. Check, then render
```bash
python <skill>/scripts/render.py film/storyboard.json --check
python <skill>/scripts/render.py film/storyboard.json --stills film/sheet.png
```
Open the sheet and compare it with the site: same colours, same type, same corners? Do the captions read
like the samples in voice.md — same language, same address (je/u), same tone? Captions readable,
nothing overlapping, pieces cropped cleanly, every list item and piece visible? Fix, re-check, then:
```bash
python <skill>/scripts/render.py film/storyboard.json --out film/promo.mp4
```
Add `--lens 0` for flat brands (most websites): the default lens adds grain, bloom and a vignette that
the site itself doesn't have.
Flat stagings render in about a minute; 3D devices take ~0.7 s per frame per worker (`--workers`).

## 6. Deliver
Send the MP4 with a short note: the direction and why, the brief, the voice in one line (language, address, register, and which
captions are the project's own words), the style decisions (motion, staging, which fonts/colours came
from the project), and the CC0 track used (default: "Make Funk" by HoliznaCC0). Offer next steps: a
vertical cut (`--format vertical`), a longer 30 s version with a customer quote, their own track, or a
slower motion personality.

## Boundaries
- Only true claims and real quotes from the project. No invented testimonials, clients, numbers or ratings.
- Use the person's own photos/work from their project only; don't pull images of people from the web.
- No Apple trademarks or device lookalikes; the `phone` frame is generic. The same goes for operating
  system UI: no fake lock screens, "9:41" status bars, island-style call banners or OS notification
  styling. In `choreography`, the stacked cards are the project's own UI in the project's own style.
- Bundled fonts (Inter, JetBrains Mono) are OFL; bundled music is CC0. Project fonts are used only for
  rendering the user's own film.