# Visitors: showing Burning items vs filed to-dos (design pass, 2026-10-31)

Owner: "A new piece of data to represent: the number of Burning items associated with their project/repo,
vs. the number of filed to-do items present there at all."

## What the data is today (measured from ~/dev/.lodestar/companion/now.json)
- Burning: `plots.burning.items` + `.hidden` (35 now), each with `project`, `tier` (red | amber | verify),
  `breathe`. Their `project` is a account code (A1: 28, B2: 6), NOT a repo name. A code -> repo map is missing.
- Filed to-dos: open tickets per repo (`ticket list --all`: granite 40, lodestar 33, certanum 28, ...).
- They are different populations (urgent asks vs filed tickets), so "burning out of all" needs a definition.
- Both are per PROJECT and change slowly (minutes to days); session data changes in seconds. A project
  with burning items but no open Claude session has no creature today.

## Channels already taken (GRAMMAR_V2)
size = memory · internal tempo = CPU · satellites = background tasks · in-shape pulses = bandwidth ·
red glow + disalignment = machine strain · ripples + approach = needs you · hue + form = identity.
So Burning may not use red glow (strain), ripples (needs you), orbiting things (tasks) or the core (bandwidth).

## Concepts
1. **Running lights** (recommended). A short fixed strip of tiny pips on the creature's underside, like a
   craft's running lights. One pip per to-do (beyond 12, pips group and the strip lengthens by sqrt).
   Unlit pips are faint glass. Burning ones are lit and flicker like a candle (irregular, slow). Red-tier
   burning gets a faster flicker; amber a slow one. Lit fraction = burning share; strip length = backlog.
   It is static structure, so it reads at a glance and never competes with the motion channels.
   Per concept: Choir, pips under the saucer rim. Siphonophores, pips around the bell's skirt.
   Sigils, the glyph's bottom row becomes an 8-bit status bar. Kaleidoscope, an outer bead ring.
   Fireflies, a fixed bead tail.
2. **Lantern.** A small lantern hangs from the creature on a thread (anglerfish lure). Lantern size =
   total to-dos, flame brightness and flicker = burning count. A separate object, so it is clear; but it
   adds a second thing per creature and may read as a satellite.
3. **Crown.** A thin arc above the creature, a gauge: arc length = backlog, the burning segment glows hot
   white. The most exact, the least magical.
4. **Ember stars.** Burning items become a few stationary ember-stars in the sky near where the creature
   rests, gently pulsing; filed to-dos are faint dust. Beautiful and calm, but they belong to a place rather
   than to the creature, so identity is weaker.
5. **Ghost visitor.** For projects with burning items and NO open session: a faint, slow, almost-still
   creature of that project's form drifts at the screen's edge, its running lights lit. It is the only way
   burning work in a closed project can be seen. It combines with any of 1-4.

## Colour
Burning tiers are red and amber in Lodestar, but red here means machine strain, and amber collides with
amber project hues. So tiers are carried by flicker rhythm and brightness (white-gold flame), not by red.

## Rulings (owner, 2026-10-31)
1. Running lights count BURNING items only, not tickets.
2. Lodestar, not Sprites, attributes burning items to projects (Lodestar ticket BURNING_WIRE_TO_PROJECTS); anything not
   tied to a watched project counts on the Lodestar creature. Sprites reads a per-project burning count from the feed
   (Augur `projects[].counts.burning`); absent = no lights.
3. Two sessions in one project: lights on ONE creature only, the oldest session.
4. Ghost visitors: yes. A project with burning > 0 and no session gets a faint, slow, almost-still creature of its form at
   the screen edge with its lights lit.
5. Lodestar: "The lodestar sprite looks the same as when Lodestar is opened... the same user decided images. But when
   it's closed, it's a ghost." and "If there's truly nothing burning, then Lodestar ghost fades like any other." So no
   special look and no always-on case: same ghost rule as every project.
6. "White sprites just draw randomly from the range of possibilities, like any new project not yet selected by the user."
   An unmanaged project's sprite: random species and form, coloured white, no counts.
