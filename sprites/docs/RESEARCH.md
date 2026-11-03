# Ambient desktop pets: research report (2026-10-31)
Source: GPT research consult (full text: ~/ClaudeWork/sprites/research/consult_out.txt, id 20261031T120637-SidePulse-literature_review). Load-bearing URLs below returned HTTP 200 on a direct fetch (red3d.com returned 403 to curl, likely bot-blocking; it is the canonical boids page). Claims are leads, not measurements; no Apple Silicon power numbers exist in any source.

## A. Prior art
- Shijima-Qt (Shimeji for macOS/Qt; uses Accessibility for frontmost-window tracking; ARCHIVED 2026-04-29, GPL-3.0, ~200 stars): https://github.com/pixelomer/Shijima-Qt
- eSheep https://github.com/Adrianotiger/desktopPet ; oneko https://github.com/tie/oneko ; Desktop Goose https://samperson.itch.io/desktop-goose (cursor-stealing is what annoys; keep any mischief opt-in).
- BonziBuddy FTC complaint (privacy lesson: never read screen contents) https://www.ftc.gov/system/files/documents/cases/040217compbonzi.pdf
- Closest functional precedent: RunCat (speed = CPU; ~1.1% CPU reported by one user) https://kyome.io/runcat/index.html?lang=en
- Agent-reactive pets: AgentPet (Swift/SwiftUI, 394 stars, last commit 2026-10-22, MIT) https://github.com/ntd4996/agentpet ; BongoCat https://github.com/ayangweb/BongoCat ; OpenPets https://openpets.dev/ . No mature turnkey CI pet verified.
- User reports (anecdotes): works = quiet companionship, nostalgia, rare amusing events (https://www.reddit.com/r/macapps/comments/1lt3az3/, https://news.ycombinator.com/item?id=40793465). Annoys = pointer stealing/interruption (https://www.reddit.com/r/techsupport/comments/1ge24x5/friend_installed_desktop_goose_and_nothing_i_do/), CPU cost of monitoring tools, requests for a "meeting mode" (https://www.reddit.com/r/macapps/comments/1v9vaty/wallpets_expressive_animal_companions_that_live/), novelty fades unless the pet signals something useful (https://www.reddit.com/r/AI_Agents/comments/1tv89uj/would_you_guys_pay_for_an_ai_desktop_pet_that/). Tamagotchi lesson: keep growth, drop neglect/death penalties.
- Calm tech: Weiser & Brown https://calmtech.com/papers/designing-calm-technology (Jeremijenko's Dangling String = network traffic as motion, a direct ancestor of bandwidth-driven drift); Amber Case https://calmtech.com/ ; ambientROOM https://tangible.media.mit.edu/project/ambientroom/ ; Ambient Orb (one colour-to-data mapping) ; glanceable displays https://www2.eecs.berkeley.edu/Pubs/TechRpts/2006/EECS-2006-113.html . Anadol/Ikeda: borrow texture and grid rhythm, cut the spectacle, keep each metric's meaning stable.

## B. macOS overlay
- Recipe: borderless nonactivating NSPanel, isOpaque=false, clear background, hidesOnDeactivate=false, ignoresMouseEvents=true, accessory activation policy, level .screenSaver, collectionBehavior [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary] (+ newer .canJoinAllApplications). Apple DTS tested this on macOS 26; .floating/.statusBar were insufficient: https://developer.apple.com/forums/thread/826308 . Verify separately on macOS 15.
- Focused window frame: AXUIElement (frontmost app, kAXFocusedWindowAttribute) needs Accessibility trust; AX observers give change notifications. Fallback CGWindowListCopyWindowInfo gives bounds/owner/PID without Screen Recording (titles need it) but not true keyboard focus (z-order heuristic): https://developer.apple.com/videos/play/wwdc2019/701/
- Screen sharing: do NOT rely on sharingType = .none; Apple calls it legacy and says ScreenCaptureKit can still capture the window: https://developer.apple.com/documentation/appkit/nswindow/sharingtype-swift.enum/none . Plan: explicit meeting-mode hotkey, plus auto-hide when a screen-share/capture is detected (our own heuristic), since we cannot filter other apps' captures.
- Multi-display: one panel per NSScreen, shared simulation, rebuild on NSApplication.didChangeScreenParametersNotification.
- Telemetry: sample every 1-2 s independent of drawing; per-process net via nettop is costly (Stats issue https://github.com/exelban/stats/issues/3499).

## C. Rendering stacks (beauty per effort; costs are estimates, no sourced Apple Silicon benchmarks)
1. SpriteKit: transparent scenes, particles, additive glow textures; preferredFramesPerSecond/isPaused for throttling; avoid SKEffectNode blur. https://developer.apple.com/documentation/spritekit/creating-a-scene-with-a-transparent-background
2. SwiftUI Canvas + TimelineView + .layerEffect Metal shaders: best for grids/morphing geometry; fastest prototype. https://developer.apple.com/documentation/swiftui/view/layereffect%28_%3Amaxsampleoffset%3Aisenabled%3A%29
3. CAEmitterLayer: cheap sparkle; weak for interacting individuals.
4. Rive: great authored characters, state machines + data binding, Apple runtime supports AppKit/SwiftUI on macOS https://rive.app/docs/runtimes/apple/apple ; better for mascots than procedural LED glyphs.
5. Metal/MetalKit + bloom: max control, most effort; keep bloom buffers small/low-res. https://developer.apple.com/documentation/metalkit/mtkview
6. WKWebView/WebGL (three.js, regl, p5, shadertoy), Tauri (2.12.1 dropped private-API flag for transparency https://v2.tauri.app/release/tauri/v2.12.1/), Electron, Godot, Lottie: more power/memory overhead and awkward Spaces/fullscreen behaviour; Lottie is for canned loops.
- Throttling: 20-30 fps while drifting, 5-10 when idle/sleeping, pause when hidden, reduce under Low Power Mode/thermal pressure, coalesce timers; measure WindowServer too. Reported figures: Desktop-Overlay ~1-1.5% of a core on 2019 Intel i9; Fluffel claims <2% idle (unverified).
- Forkable: AgentPet (above); xiangking/agent-pet (Tauri, transparent sprite window, WebSocket events, 22 stars, 2026-06-18) https://github.com/xiangking/agent-pet ; pet-therapy (SwiftUI, window obstacles, 8 stars, 2022) https://github.com/raman0c17/pet-therapy ; Desktop-Overlay (native panels + metrics, 2 stars, 2026-10-28) https://github.com/alhanashi/Desktop-Overlay ; Stats (telemetry reference) https://github.com/exelban/stats .

## D. Behaviour
- Reynolds boids https://www.red3d.com/cwr/boids/ and steering https://www.red3d.com/cwr/papers/1999/gdc99steer.html : wander + separation + obstacle avoidance (inflate focused-window rect by margin, highest priority); weak cohesion, capped speed/accel.
- Curl noise for drift (Bridson) https://www.cs.ubc.ca/~rbridson/docs/bridson-siggraph2007-curlnoise.pdf ; apply to desired velocity, not position.
- Libraries: GameplayKit (GKAgent2D, GKGoal flocking, GKStateMachine, GKNoise) https://developer.apple.com/documentation/gameplaykit ; Yuka (JS) https://github.com/Mugen87/yuka .
- State machine: sleep, drift, avoid, socialize, signal, with cooldowns and hysteresis. Encoding: CPU = pulse tempo; memory pressure = density/contraction; bandwidth = directional spark trains; session identity = stable glyph shape, activity = brightness; keep travel speed independent of load.

## Recommendation
1. AppKit NSPanel + SpriteKit + GameplayKit: best all-round (particles, interaction, steering built in).
2. NSPanel + SwiftUI Canvas/TimelineView + Metal layerEffect shaders: fastest route to the LED-grid / morphing-glyph look; combine with own boids code.
3. NSPanel + MetalKit with low-res bloom: only if 1 or 2 cannot hit the look.
Avoid web/Electron/Godot hosts for an always-on overlay. Fork AgentPet or Desktop-Overlay for panel plumbing, not art.
