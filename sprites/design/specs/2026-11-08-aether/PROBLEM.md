# Aether — the problem, in the owner's words (2026-11-08)

> At the same time, we just saw Moby in concern and observed his stage have the most amazing green glowing dots
> floating on a massive screen behind him. It was strongly reminiscent of Asteroids, tiny dots bouncing and
> interacting and colliding, occasionally merging into something larger, then breaking up again. Sometimes arranging
> themselves into small linear structures that floated and rotated, only to disitegrate again later. Please do a
> design pass on how we might have THIS added as the "environment" the Sprites live in. These dots would only live
> outside windows of any kind, focus or no, and bounce off the boundaries. They would be "pushed out of the way" as
> windows are moved around, getting hotter or colder as they expanded similar to the ideal gas law demonstrated
> through particle kinetics. And they would do complex things as the Sprites passed by, as though interacting with a
> complex magnetic and electric field near the Sprites. This would take the place of the slowly moving background, so
> the background would be utterly black and these would add the visual interest. Settings would determine their
> average temperature when they enter the screen: are they relatively "hot" so fast moving? Are they relatively cool
> so barely moving unless struck? Do they constantly enter the screen from a reservoir and freely leave, or are the
> boundaries reflecting? What's the density of the dots? How often do they start to build small temporary vector
> structures by joining together? Do a deep design pass on this concept. Expand it, improve it, and make it a really
> fun interactive background that isn't obtrusive or get in the way during normal work but adds a whimsical note
> while performing normal computer usage. How might they interact with icons on the desktop? The small tray in the
> upper right? Shortcuts? Have fun with this idea, and impress us. Look through repo's for similar ideas and
> especially how to keep this low CPU usage. Then send the whole concept to GPT for skeptical review and improvement
> blind. Finally combine it all together and question card me to finis the refinement and let's get it done! We'll
> call them the aether. Particle size.

("Particle size" at the end: a further Settings dimension.)

## Context a reader needs
- Sprites: a native macOS overlay app (Swift + WKWebView canvas, `sprites/app/macos/`, `sprites/app/stage.html`)
  drawing one luminous creature per Claude Code session, on every Space, kept away from the focused window.
  11 species, each a JS piece on a shared runtime (`sprites/prototype/visitors_runtime.js`).
- Today's background: "backdrops" — 12 slowly moving shader backdrops (`sprites/app/backdrops/`, `Backdrop.swift`,
  catalog.json, chosen in Settings → Backdrop, with a speed setting). The Aether would replace these with pure
  black plus particles.
- The app already knows window rectangles (it avoids the focused window) and has a desktop-icon dimming layer.
- Low CPU is a hard requirement: it runs all day on a laptop on battery.
