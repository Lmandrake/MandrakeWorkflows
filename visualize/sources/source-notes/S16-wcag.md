# S16 — WCAG 2.2 Understanding: SC 1.4.3 Contrast (Minimum) & SC 1.4.1 Use of Color (W3C/WAI)

## Authority / evidence type
Tier A (as a standard). W3C Web Content Accessibility Guidelines 2.2 — the normative international accessibility standard. Note the *Understanding* documents captured here are explicitly "informative explanations, not required to meet WCAG"; the normative statements are the Success Criteria themselves (quoted verbatim below). Contrast thresholds are grounded in ergonomics standards ([ISO-9241-3], [ANSI-HFES-100-1988]) and vision-science findings ([ARDITI-FAYE], [GITTINGS-FOZARD]). Authoritative for *web UI*; must be translated with care to static scientific figures and slides (see caveats).

## Scope
Two success criteria for perceivable content:
- SC 1.4.3 Contrast (Minimum), Level AA — luminance contrast between text and background.
- SC 1.4.1 Use of Color, Level A — colour must not be the sole means of conveying information.
Both target web content and UI; applied here as a lens for figures, slides, and dashboards.

## Central claims
- SC 1.4.3 (normative): visual presentation of text and images of text must have a contrast ratio of at least **4.5:1**, except: large-scale text ≥ **3:1**; incidental/decorative/invisible text and text in logos have no contrast requirement.
- "Large-scale" = at least 18 pt, or 14 pt bold (≈ 24 px / 18.5 px; ≈ 1.5 em / 1.2 em) — larger/heavier strokes stay readable at lower contrast.
- Contrast ratio = (L1 + 0.05) / (L2 + 0.05), L1 = lighter and L2 = darker relative luminance; range 1:1 to 21:1. Relative luminance for sRGB: L = 0.2126·R + 0.7152·G + 0.0722·B after the gamma-linearization given.
- Contrast is computed so that colour (hue) is not a key factor — luminance contrast serves low-vision and CVD readers regardless of hue; ratios are thresholds and computed values must not be rounded up (4.499:1 fails 4.5:1).
- Rationale: 3:1 is the ANSI minimum for normal vision; 4.5:1 compensates for ~20/40 acuity (≈ age-80 elders) and congenital/acquired colour deficiency; 7:1 (AAA / SC 1.4.6) compensates for ~20/80.
- Charts/graphs/diagrams and other non-text content are covered not by 1.4.3 but by SC 1.4.11 Non-Text Contrast (referenced, not captured here).
- SC 1.4.1 (normative): "Color is not used as the only visual means of conveying information, indicating an action, prompting a response, or distinguishing a visual element." (Level A)
- Not everyone perceives colour the same way (partial sight, older users, monochrome displays, CVD); information carried by colour differences alone may be lost.
- A lightness/luminance difference can count as an *additional* visual distinction if the contrast ratio between the colours is ≥ 3:1; but if reading requires perceiving a *particular* colour (e.g., green = valid vs red = invalid), an additional non-colour indicator is required regardless of contrast.

## Operationalizable rules
- Provide ≥ 4.5:1 luminance contrast for normal text against its background; ≥ 3:1 for large text (≥ 18 pt, or ≥ 14 pt bold).
- Do not round contrast up to meet the threshold; compute against the specified/adjacent background.
- Aim above the minimum for thin/unusual fonts (anti-aliasing can lower effective contrast); prefer thicker strokes.
- Never rely on colour alone to convey meaning, indicate state, prompt action, or distinguish elements — add a redundant cue: text/label, shape, icon, pattern, or position (WCAG technique G111 = colour + pattern; G14 = information also available in text; G183 = ≥3:1 contrast to distinguish inline links).
- A hue difference plus a lightness difference (≥ 3:1 contrast) can serve as the redundant distinction; a hue difference alone does not.
- For images conveying information by colour, also convey it in text/legend (e.g., numbered elements with a legend; icons beside colour-coded labels).

## Important caveats
- **Web-UI norms, translate with care.** These criteria are written for rendered web text/UI where the user agent supplies foreground/background colours; applying the 4.5:1 / 3:1 numbers to *scientific figures and slides* is a reasonable adaptation but is not a WCAG requirement for print figures, and the point-size definitions of "large text" depend on rendered CSS px, not a figure's physical size or a projected slide's apparent size.
- SC 1.4.3 covers **text and images of text only** — not data marks, lines, or fills in a chart. Contrast of chart elements themselves falls under SC 1.4.11 Non-Text Contrast (not in the captured excerpts), so do not cite 1.4.3's 4.5:1 for, e.g., a line-vs-background in a plot.
- Exceptions (incidental, decorative, logos, inactive UI components) mean not all text must meet the ratio.
- "Colour is not the sole means" (1.4.1) is about redundant encoding, not about which colours to use; it does not by itself mandate CVD-safe palettes (that combines with S05/S06). Conversely, meeting a contrast ratio does not satisfy 1.4.1 if a particular hue must be perceived.
- Contrast math assumes sRGB and specified background (white assumed if none specified); dithering/anti-aliasing handling has specific notes.

## Conflicts with other guidance
- Complements S05 (Crameri) and S06 (Nature): S16 supplies the redundancy principle (don't rely on colour alone) and the luminance-contrast thresholds that underlie S06's ">4.5 contrast ratio" text rule; S05/S06 supply the CVD-safe colour-map/palette content S16 does not.
- Mild reconciliation with S06: WCAG technique G111 explicitly endorses colour + pattern as a redundant cue, whereas S06 tells authors to *avoid patterns* and instead use solid colours with keys/keylines. Both satisfy the underlying goal (a non-colour-dependent distinction) via different mechanisms — keys/labels vs patterns.
- No direct conflict with S03; S03's "strong contrast for projection" is consistent with S16's luminance-contrast emphasis.

## Useful examples
- 1.4.1: a form marking required fields with red text *and* an icon (and a text instruction) so CVD users still perceive the requirement.
- 1.4.1: an SVG chemical-compound diagram where elements are identified by colour *and* by numbers with a legend — sighted CVD users read the numbers.
- 1.4.3: 18 pt / 14 pt-bold "large text" threshold allowing 3:1 instead of 4.5:1; worked acuity rationale (20/40 → 4.5:1, 20/80 → 7:1).

## Candidate principle IDs
- [ACCESS] Never use colour as the only means to convey information, indicate state, prompt action, or distinguish elements — add a redundant text, shape, icon, pattern, or position cue. | force: MUST | tier: A | contexts: figures, slides, dashboards, UI | rationale: WCAG 2.2 SC 1.4.1 (Level A); colour-only cues are lost to CVD/low-vision/monochrome viewers | source: S16
- [ACCESS] Provide luminance contrast of at least 4.5:1 for normal text and 3:1 for large text (≥18 pt or ≥14 pt bold) against its background. | force: MUST | tier: A | contexts: text on figures/slides/UI (translate to print with care) | rationale: WCAG 2.2 SC 1.4.3 (Level AA); compensates for ~20/40 acuity and colour deficiency | source: S16
- [ACCESS] Treat the contrast ratios as hard thresholds — compute (do not round up) contrast against the actual adjacent background. | force: MUST | tier: A | contexts: contrast checking | rationale: 4.499:1 does not meet 4.5:1 | source: S16
- [ACCESS] When distinguishing elements by colour, ensure the colours also differ in lightness (≥3:1 contrast) so the distinction survives colour-vision deficiency; a hue-only difference is insufficient. | force: SHOULD | tier: A | contexts: categorical colour encoding | rationale: SC 1.4.1 note — luminance difference counts as an additional visual distinction | source: S16
- [ACCESS] Prefer thicker/heavier font strokes or exceed the minimum contrast for thin or unusual fonts. | force: SHOULD | tier: A | contexts: typography on figures/slides | rationale: anti-aliasing can drop effective contrast below the nominal ratio | source: S16
- [QA] Verify text contrast with a luminance-contrast tool and confirm every colour-coded distinction has a non-colour backup before publishing. | force: SHOULD | tier: A | contexts: accessibility QA | rationale: operationalizes SC 1.4.3 and 1.4.1 | source: S16
```
