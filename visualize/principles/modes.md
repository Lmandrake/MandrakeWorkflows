# Modes: which constraints are always on, and which you ask for

Shared by both families: CLEAR (`skills/v0.1/`) and BEAUTIFUL (`skills/beautiful/`). Every
skill that checks colour, contrast, print or accessibility reads this table rather than
hard-coding a requirement.

A request or scene carries `modes: [...]`. With no modes you get the **default**: office use,
technical interchange meetings and workshops. That is a screen or a meeting-room projector, an
expert audience, the presenter in the room, and full colour bandwidth. Modes combine
(`[projector, colorblind_safe]`); `journal` is the only bundle.

**Infer a mode only from a stated destination** ("for the paper" → `journal`, "public site" →
`accessible_web`, "keynote" → `projector`). Never add `colorblind_safe` or `print_grayscale` by
habit: they cost most of the hue space and are opt-in.

## 1. The modes

| Mode | Invoke for | What it turns on |
|---|---|---|
| *(default)* | Office, technical meetings, workshops, working sessions | The truth floor (section 3) plus the default habits: key at the point of use when values must be read; legible text (about 3:1 against its own background); no clipped or colliding text or keys; units; short caption and colophon. Any palette, rainbow and turbo included, never jet. No CVD, grayscale, WCAG, print or archival checks |
| `colorblind_safe` | Journals; any audience you cannot vouch for | CVD-safe palette (no confusable hues at similar lightness, ACCESS-02); categories differ in lightness as well as hue (ACCESS-04); a non-colour route for every required distinction: label, shape, position or readout (ACCESS-01); a CVD simulation of the delivered image |
| `print_grayscale` | Paper, printable PDF, a black-and-white printout | Monotone-lightness maps (COLOR-02); every distinction survives grayscale (ACCESS-05); vector or at least 300 dpi, never upsampled (MEDIA-03); type and line weights checked at print size |
| `projector` | Big room, keynote, plenary, washed-out projector | One idea per view; larger type and thicker lines (MEDIA-01); text contrast about 4.5:1 (ACCESS-03); direct labels, not a legend (ANNO-01); fine context dropped |
| `accessible_web` | Public web pages; anything posted outside the institution | Includes `colorblind_safe`; WCAG text contrast 4.5:1 normal, 3:1 large and keys (ACCESS-03); alt text and long description (ANNO-09); keyboard-operable controls; reduced-motion fallback; licence check on every source and renderer |
| `lay_audience` | Outreach, press, public talks, non-specialist decision makers | Insight title stating the takeaway (ANNO-02); a "how to read this" caption line; uncertainty as natural frequencies; a line forestalling causal reading (ANNO-08); more scaffolding, less density |
| `archival` | Results you will cite, defend or rebuild years from now; releases | Full colophon; inputs archived or their durable source recorded; licence check; renderer config diff and effect on/off tests; reproducible from the scene file on a second run |
| `journal` *(bundle)* | Submitting a figure to a journal | `colorblind_safe` + `archival`, plus vector or at least 300 dpi with type checked at print size; full standalone caption (ANNO-03); source on the figure (ANNO-06); axis lines, ticks and units (ANNO-05); aligned panels; uncertainty wherever the data has it. **Grayscale survival is not required**; ask for `print_grayscale` separately |

## 2. Gates by family and mode

Gates are defined in `evaluation/RUBRIC.md`. **Floor** = always on in both families and every
mode. Mode columns list only what the mode adds.

| Gate | Floor (always) | CLEAR default | BEAUTIFUL default | Added by modes |
|---|---|---|---|---|
| G1 Magnitude honesty | Bars at zero; area ∝ value; no 3-D height to compare non-spatial amounts; shared scale across panels; exaggeration and non-scale sizing disclosed | hard | hard | — |
| G2 Quantifiability | Units present; mapping disclosed (key or colophon) | Colour bar on canvas; axis units and ticks | Key at the point of use whenever the piece asks for value or order reading; otherwise the colophon may carry it | `journal`: axis lines, ticks, units |
| G3 Colour accessibility | Every required distinction is visible to the intended viewer in the intended medium | **No CVD or grayscale requirement** | **No CVD or grayscale requirement**; decorative hue exempt | `colorblind_safe` (and `journal`, `accessible_web`): ACCESS-01, -02, -04 and the CVD check. `print_grayscale`: ACCESS-05, COLOR-02 grayscale survival |
| G4 Text contrast | Data-bearing text legible against its own background (about 3:1) | hard at that floor | hard at that floor | `projector`, `accessible_web`: 4.5:1 normal, 3:1 large and keys |
| G5 Colormap validity | Never jet; map class fits the data (COLOR-04); no silent clamp; a lifted or trimmed map is recorded | Perceptually uniform (COLOR-01); no rainbow or turbo unless a reason is recorded | Rainbow and turbo allowed if declared, over the full data range, with a key or readout that gives the order | `colorblind_safe`: a CVD-safe map |
| G6 Scientific disclosure | Simulated, modelled and derived content labelled; every visible element is data or declared decoration; renderer effects bound or off | No decoration (LAYOUT-01) | Decoration and effects allowed, declared | `archival`: each effect tested on and off |
| G7 Hierarchy | Keys, units and essential caveats visible and near what they qualify | One primary element (HIER-01) | Artistic hierarchy free | `projector`: one idea per view |
| G8 Render integrity | No clipped or colliding text or keys; required marks survive compositing | hard; hairball is blocking | hard | — |
| G9 Network legibility | Say whether a group is a source attribute, an algorithm result or the layout; layout and parameters in the colophon | Matrix where a hairball would result (NET-02) | Force and embedding layouts allowed with a reading guide | — |
| G10 Self-containment | A short caption (what it is, real data, mapping) and a colophon naming sources | hard | two tiers: caption at the piece, colophon one click away | `journal`: full standalone caption, source on the figure |
| G11 Intent match | The agent reads back the render and compares | Against the takeaway | Against the aesthetic intent and required readings | `lay_audience`: insight title |
| G12 Claim–encoding consistency | always | hard | hard | — |
| G13 Aggregation honesty | Aggregation (KDE, hexbin, bundling, LOD, interpolation) disclosed with parameters | hard | hard | `archival`: effect on required readings tested |

## 3. Principles that are mode-dependent

The registry entries keep their force; this table says when they apply.

| Principle | Applies when |
|---|---|
| ACCESS-01 colour never the sole cue | `colorblind_safe`, `journal`, `accessible_web`. In the default, a non-colour route is still needed for any distinction the reader must make without the key |
| ACCESS-02 CVD-safe palette | `colorblind_safe`, `journal`, `accessible_web` |
| ACCESS-03 4.5:1 / 3:1 contrast | `projector`, `accessible_web`. Default: legible, about 3:1 |
| ACCESS-04 lightness difference between categories | `colorblind_safe`, `journal`, `accessible_web` |
| ACCESS-05 grayscale first | `print_grayscale` only |
| COLOR-02 monotone lightness | Default for ordered fields in CLEAR; off when a key or readout gives the order. Grayscale survival half: `print_grayscale` only |
| COLOR-03 no rainbow | CLEAR default, switchable with a recorded reason. BEAUTIFUL: allowed per G5 above. Jet: never |
| COLOR-06 grey first | CLEAR only |
| ANNO-02 insight title | CLEAR default; `lay_audience`; off for BEAUTIFUL |
| ANNO-09 alt text | `accessible_web` |
| MEDIA-03 vector or 300 dpi | `print_grayscale`, `journal` |

## 4. The truth floor, in one list

Real data; simulated and derived layers labelled. The mapping disclosed, and the drawn colours
really follow it. No silent clamp; never jet; map class fits the data. Units; essential caveats
near what they qualify; sources named. Magnitude honesty (G1). Unsupported derived values never
shown as real values (a validity mask, not zeros). Headline claims checkable against the
encoding; aggregation disclosed. Effects and decoration declared; renderer hidden defaults bound
or off. Network groups say what they mean. Animation states data time against playback time and
any interpolation, and flashes no more than 3 times a second. Look at the actual render at final
size. Reproducible from the scene file.
