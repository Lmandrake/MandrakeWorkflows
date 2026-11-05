# Hover labels: shortnames and five name designs (2026-11-01)

Owner, 2026-11-01 ~06:00: "We should have shortnames for the long-named critters, and when I hover over them their names
should be beautiful and in the right color, not ugly, large white text please. Do some design work and give me some options
on how the name appears, as beautiful as the Sprites themselves."

Status: owner ruling ~06:40, verbatim: "Implement ALL of those label options switchable in the settings menu, with
Constellation as the default." Settings and the labels module are built. The stage call site is NOT wired yet: another agent is
rewriting the stage into one shared canvas, and the wiring note for it is in "Integration" below.

## Shortnames
Code: `prototype/labels/shortname.js` (`SpritesShortNames.shortNames([{name, alias?, short?}])`).
Rule, in order:
1. **Settings override** (`short` per project, saved in cast.json beside concept/iv/hex; max 12 characters) wins.
2. **Waypoint launch alias** when it is up to 10 characters and differs from the name (MicrosoftGraphAccess -> MSGRAPH,
   KestrelWorks_Mandrake -> KesMine). Names come from the Lodestar registry (Augur's `project`), aliases from
   ~/dev/Waypoint/launches.md.
3. **Automatic**: split on `_ - .` and CamelCase; drop the owner word "Mandrake" when anything is left; keep the whole name
   if it is up to 12 characters; else keep leading whole words while up to 10 characters; a result under 5 characters
   takes the whole name if up to 12, else adds the initials of the rest (NASA-Guidance-Docs -> NASA GD).
4. **Distinct**: colliders take their next word if it fits in 12, else the initials of the rest, else a number.
   `_` and `-` display as spaces. The table below is generated from all 79 registry projects: all distinct, at most 12 characters.

Settings change (proposed, not built): one "Short name" text field on each project row, with the automatic
name as placeholder text.

| Project (registry Name) | Focus | Colour | Shortname | Source |
|---|---|---|---|---|
| Orchard_Mandrake | yes | #CB50F0 | **Orchard** | auto |
| ProjectCert_Mandrake | yes | #3388EE | **ProjectCert** | auto |
| ProjectDial | yes | #66BB22 | **ProjectDial** | auto |
| Atlas | yes | #B5FF00 | **Atlas** | auto |
| Ember28 | yes | #8888EE | **Ember28** | auto |
| Lodestar | yes | #FFCA42 | **Lodestar** | auto |
| KestrelWorks | yes | #40C888 | **KestrelWorks** | auto |
| Granite | yes | #22DDAA | **Granite** | auto |
| StayCurrent | yes | #00B5B5 | **StayCurrent** | auto |
| agentic_experiment_orchestration |  | (hashed) | **agentic** | auto |
| Bridge |  | (hashed) | **Bridge** | auto |
| ChatGPTConsult |  | (hashed) | **ChatGPT** | auto |
| claude-remote-control |  | (hashed) | **claude** | auto |
| cocaffeinate |  | (hashed) | **cocaffeinate** | auto |
| confident-wrong-numbers |  | (hashed) | **confident** | auto |
| Consilience |  | (hashed) | **Consilience** | auto |
| ConsultPeer |  | (hashed) | **ConsultPeer** | auto |
| Custos |  | (hashed) | **Custos** | auto |
| DataArt |  | (hashed) | **DataArt** | auto |
| Dispatch |  | (hashed) | **Dispatch** | auto |
| DispatchChat |  | (hashed) | **DispatchChat** | auto, made distinct |
| DispatchOpenCode |  | (hashed) | **DispatchOpen** | auto, made distinct |
| EvidenceBoundPapers |  | (hashed) | **Evidence** | auto |
| Fetcher |  | (hashed) | **Fetcher** | auto |
| Fleetview |  | (hashed) | **Fleetview** | auto |
| GameDesignContent |  | (hashed) | **GameDesign** | auto |
| api_gateway |  | (hashed) | **api gateway** | auto |
| GenAISwitch |  | (hashed) | **GenAISwitch** | auto |
| git_efficiency |  | (hashed) | **git E** | auto |
| Hearthview |  | (hashed) | **Hearthview** | auto |
| Hermes_Mandrake |  | (hashed) | **Hermes** | auto |
| Hestia |  | #EECC22 | **Hestia** | auto |
| Ideogram |  | (hashed) | **Ideogram** | auto |
| image-scaling |  | (hashed) | **image** | auto |
| private-store |  | (hashed) | **private store** | auto |
| Lidocaine |  | (hashed) | **Lidocaine** | auto |
| Machinist |  | (hashed) | **Machinist** | auto |
| Mail |  | (hashed) | **Mail** | auto |
| MandrakeAudio |  | (hashed) | **Audio** | auto |
| MandrakeEmacs |  | (hashed) | **Emacs** | auto |
| MandrakePrivateData |  | (hashed) | **PrivateData** | auto |
| MandrakeVisualize |  | (hashed) | **Visualize** | auto |
| MandrakeWorkflows |  | (hashed) | **Workflows** | auto |
| measuring-large-artifacts |  | (hashed) | **measuring** | auto |
| MicrosoftGraphAccess |  | #3060F0 | **MSGRAPH** | alias |
| Modality |  | (hashed) | **Modality** | auto |
| NASA-Guidance-Docs |  | (hashed) | **NASA GD** | auto |
| Nemotron_Bridge |  | (hashed) | **Nemotron** | auto |
| NewHarness |  | (hashed) | **NewHarness** | auto |
| KestrelWorks_Mandrake |  | #40C888 | **KesMine** | alias |
| Nightlight |  | (hashed) | **Nightlight** | auto |
| Orgscan |  | (hashed) | **Orgscan** | auto |
| parallel-agent-worktrees |  | (hashed) | **parallel** | auto |
| PersonalComms |  | (hashed) | **Personal** | auto |
| Placard |  | (hashed) | **Placard** | auto |
| PlaudAccess |  | (hashed) | **PlaudAccess** | auto |
| ProjectPsy_Mandrake |  | (hashed) | **ProjectPsy** | auto |
| QuestionCard |  | (hashed) | **QuestionCard** | auto |
| Relevant_Transcripts |  | (hashed) | **Relevant** | auto |
| Repo |  | (hashed) | **Repo** | auto |
| resumable-batch-jobs |  | (hashed) | **resumable** | auto |
| review-sheet |  | (hashed) | **review sheet** | auto |
| RimMandrake |  | (hashed) | **Rim** | auto |
| search-when-words-differ |  | (hashed) | **search** | auto |
| ShortRequest_dev |  | (hashed) | **Short** | auto |
| SidePulse |  | (hashed) | **SidePulse** | auto |
| SlackMaster |  | (hashed) | **SlackMaster** | auto |
| Tracker |  | (hashed) | **Tracker** | auto |
| verify-model-quotes |  | (hashed) | **verify** | auto |
| VizSkillLab |  | (hashed) | **VizSkillLab** | auto |
| Waypoint |  | (hashed) | **Waypoint** | auto |
| Wisps |  | (hashed) | **Wisps** | auto |

## Five label designs
Code: `prototype/labels/labels.js` (`SpritesLabels.draw(ctx, option, label, env)`, one function per option). Mockup:
`prototype/labels/mockup.html?opt=1..5` (move the mouse over a creature to see it animate in and out; `&e=0..1` freezes the
animation at that point, `&size=0.5..2` matches the Size slider). The scene is drawn from real parts: real creatures captured from
app/stage.html in live mode on a transparent background (`prototype/labels/assets/sprite_*.png`), over the real desktop
screenshot (`assets/desktop.jpg`, from ~/agent-storage/sprites/live/widgets_off.png), plus one drawn white window, since no
light window was open in that screenshot. Creatures: Lodestar (Sigils, #FFCA42) over the red wallpaper; KesMine
(KestrelWorks_Mandrake, Choir, #40C888) over the white window; Ember28 (Siphonophore, #8888EE) over a dark terminal.

Shared by all five: the label is the project's own Waypoint hue (a glow, a lighter core, never white). A soft dark halo
sits under the glyphs as a shadow, not a box, so the hue reads on the red wallpaper and on white. Cap height is 11-13 px
at 100% and scales with sqrt(Size), so 50% gives 0.71x and 200% gives 1.41x. Type stays readable at the small end and
does not shout at the large end. There is a gap of at least 6-8 px from the creature's measured extent (lopsided forms
such as Siphonophore tentacles use their own top and bottom). The label goes above the creature, or below it when there
is no room above. Each option has its own appear and disappear motion. A label is identity only and encodes no data.

| # | Option | Look | Appear / disappear | Rationale |
|---|---|---|---|---|
| 1 | **Filament** | hairline copperplate script (Snell Roundhand) with a glowing core and a tapering swash under it | a pen-light nib writes the name left to right (0.9 s); it lifts and fades upward (0.35 s) | The most "beautiful object". It reads as hand-lettered light, the same idiom as the creatures' fine luminous lines |
| 2 | **Orbit** | letterspaced Avenir capitals riding a dial arc that hugs the creature's underside (over the top near the screen bottom), with hairline ticks | letters slide out along the arc from the centre (0.8 s); fade (0.3 s) | An instrument read-out. Precise and calm, and it belongs to the creature's own geometry |
| 3 | **Constellation** | the name made of fine twinkling motes in the creature's hue | motes fly out of the creature on curved paths and settle into letters (1.2 s); they fall back into it (0.7 s) | The most magical. The name is visibly made of the creature |
| 4 | **Lantern tag** | a small smoked-glass tag hanging on a hairline thread from the creature's underside, a candle-flicker pip (the running-light idiom) and the name in rounded type | the thread drops, the tag unfolds, then the name lights (0.7 s); fade (0.3 s) | The most legible anywhere, because it carries its own dark ground. It sways a little, so it stays alive |
| 5 | **Whisper** | a Baskerville italic whose glow breathes with the creature's pulse | each letter comes into focus from a blur, left to right (0.9 s); letters drift up and blur away (0.6 s) | The quietest. It feels like the creature saying its own name |

### Self-critique (visual-critic, v1) and the one fix pass (v2)
Hard gates checked on the renders: the creature is never covered, the label is in the right hue, and the type size is
within the brief. Legibility over busy content was the weak gate.
- **Orbit v1**: on small creatures the arc wrapped about 150 degrees and the end letters stood almost vertical (the "R" of
  LODESTAR). **Fixed**: the arc is capped at about 105 degrees by widening its radius, and the ticks are shorter.
- **Constellation v1**: an 800-weight word in dense dots read as a sequinned blob; on white it was a dark slab. The fix
  (600 weight, sparser and finer motes, a lighter halo) makes it elegant on dark ground, but **on white over text it now
  washes out**. That is not solved. Constellation is for dark ground only, unless it gets a tag-like backing.
- **Whisper v1**: lowercasing broke CamelCase shortnames ("nexmine"). **Fixed**: the shortname's own case is kept.
- **Lantern tag v1**: the glass box was heavy. **Fixed**: thinner padding and border, more translucent glass.
- **Filament, Whisper, Orbit over the white window**: legible, but the dark halo shows as a grey smudge over black body
  text. Only the Tag is clean over text, because it has a ground of its own. This is the main trade-off for the owner.

Recommendation: **Lantern tag** for daily use, since it is the only one legible on every surface and it fits the running
lights. **Filament** is the more beautiful alternative if creatures mostly rest over wallpaper, which the terrain rules
prefer.

## Images (all at desktop scale, 3456x2234 for scenes)
- v2, after the fix pass (current): `~/agent-storage/sprites/labels/v2/contact_sheet.png`; per option N:
  `opt{N}_scene.png` (whole desktop), `opt{N}_close0|1|2.png` (close-ups over red, white and terminal),
  `opt{N}_animation.png` (in at 25/50/80%, shown, out at 50%), `opt{N}_size0.5.png` and `opt{N}_size2.png`.
- v1, before the fix pass: same names under `~/agent-storage/sprites/labels/v1/`.
- Render tooling (not committed, regenerable): `~/agent-storage/sprites/labels/work/render.py <tag>` (one browser, nice 19,
  waits for 1-min load < 8) and `capture_creatures.py` (recaptures the creature stills).

## Halo only over bright ground (owner ruling, 2026-11-01)
Owner: over bright backgrounds Constellation gets a soft dark halo behind its letters, only where the ground under the label is
bright; over the wallpaper and the terminal it stays pure. The same applies to Filament and Whisper. Orbit and the Tag are
unchanged: Orbit keeps its thin halo everywhere, and the Tag carries its own glass.
**Route chosen: the window rects as the proxy.** It is the cheapest reliable one: the host already sends every on-screen
window each second (`setWindows`), so this adds one boolean per window and needs no capture or permission. Rejected: a
host per-rect luminance hint, because sampling screen pixels needs Screen Recording permission and a capture every frame
or every second, for a label that shows for a few seconds.
Rule: the host marks windows of terminal apps `dark: true` (App.swift `darkApp`: iTerm2, Terminal, Warp, kitty, Ghostty,
Alacritty, WezTerm; by bundle id, cached per pid). `SpritesLabels.groundAt(windows, SpritesLabels.labelBox(x, y, r, scale, short))`
returns "bright" when the label's box overlaps any window not marked dark, and "dark" over the wallpaper or a terminal.
Known misses: a dark-themed non-terminal window (dark mode Safari, a dark IDE) counts as bright and gets a halo it does
not need, which is harmless. A white page inside a terminal (rare) gets none.
Images: `~/agent-storage/sprites/labels/v2/constellation_white_before.png` and `constellation_white_after.png`; for Filament and
Whisper, `{filament,whisper}_white_{before,after}.png`. `*_red_after.png` shows that the wallpaper stays pure.

## Integration (for the stage agent; do not edit here, wire it in the shared-canvas stage)
Load `prototype/labels/shortname.js` and `prototype/labels/labels.js` before the runtime (both are plain scripts, no
dependencies). Then three changes:
1. **Settings to the stage.** `labelStyle` arrives inside the behaviours object (`SpritesStage.setBehaviors({..., labelStyle})`,
   from ~/agent-storage/sprites/config/behaviors.json). Unknown or absent = `SpritesLabels.DEFAULT` ("constellation"). It is not a
   bool, so the code that reads behaviours as switches must skip it (`on(k)` is `B[k] !== false`, so it is safe as is).
   `hoverName: false` still turns labels off entirely. Short names: `cast.projects[name].short` overrides. Build the table once
   per cast change with `SpritesShortNames.shortNames(allNames.map(n => ({ name: n, alias: waypointAlias(n), short: cast.projects[n]?.short })))`
   and display it with `SpritesShortNames.display(...)`. In stage.html this belongs where `label:` is set for each session
   (the adapter's `sessions.push({... label: ...})`, three places plus the demo cast). The Waypoint alias is optional and can come
   from the host with the projects list.
2. **The call site.** This replaces `drawHover()` in visitors_runtime.js (today: `if (on("hoverName")) drawHover();` at the
   end of `render()`). It is drawn last, after every creature and the beacon, in the same ctx, so it is never under a
   creature. Per creature, keep `st = SpritesLabels.track(st, id === hoverId, dtWall, style)`. Use wall-clock dt, not the
   slowed sim dt, or the label animates at 10% speed while hovered. Then, while `st.phase`:
   ```js
   SpritesLabels.draw(ctx, { style, name: s.name, short: s.label, hex: s.hex /* or omit + hue: s.hue */, x: r.x, y: r.y, r: r.r,
     scale: sizeSlider /* 0.5..2, P.size / LIVE_BASE */, t: performance.now() / 1000, phase: st.phase, p: st.p,
     ground: SpritesLabels.groundAt(windows, SpritesLabels.labelBox(r.x, r.y, r.r, sizeSlider, s.label)), motes, W, H });
   ```
   Sessions carry `hue` (degrees), not hex, so pass `hue: s.hue` when there is no hex. White (unmanaged) sprites: pass
   neither, and the label is drawn neutral. Keep drawing departing labels (`phase "out"`) after `hoverId` changes, which is
   why `track` is per creature.
3. **Motes for Constellation.** The letters fly out of the creature's own lit points. The runtime does not collect them today.
   Cheapest route: an optional `V.motes(id, pts)` hook, called by each piece once per frame for the HOVERED creature only, with
   up to about 40 `[x, y]` screen points it is about to draw: Choir the rim lights, Siphonophore the bell and tentacle beads,
   Sigils the lit pixels, Kaleidoscope the petal beads, Fireflies the swarm. Points from the last frame are fine. With no
   motes, `draw` falls back to points scattered inside the creature's radius, which looks nearly the same, so the hook can
   come later.
Cost: one label at a time (the hovered creature plus at most one fading out). Constellation renders its glyph mask once per
(name, scale) and caches it, and draws about 150 to 300 dots a frame while shown. Nothing is drawn when nothing is hovered.

## Settings (built)
- **Name label** tab (`app/settings.html`, tab 3). It has five tiles, one per style, each showing the selected project's
  creature with its real label looping in, hold, out. Only the chosen and the hovered tile animate. Constellation is marked
  "default". A click saves `labelStyle` through the same `saveBehaviors` post as the switches (browser fallback:
  localStorage `sprites.behaviors`).
- **Short name** field under the project name on the Species tab. It saves `cast.projects[name].short`, and blank means
  automatic, which shows as the placeholder. Maximum 12 characters.
- Host: no new key plumbing. `saveBehaviors` and `saveCast` store any JSON object. App.swift adds `dark: true` to the
  windows of terminal apps.
- Images: `~/agent-storage/sprites/labels/v2/settings_name_label.png`, `settings_short_name.png`.
- Tests: `sprites/tests/test_labels.py`. Every style draws without throwing at scales 0.5, 1 and 2, in every phase, on both
  grounds, with and without hex. The registry shortname table is distinct and at most 12 characters, and the override wins.
  Settings round-trips `labelStyle` (default, save, reload, host init, unknown falls back) and the short name.
