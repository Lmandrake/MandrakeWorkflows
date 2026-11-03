/* The 19 behaviour switches (owner, 2026-10-31): every one default ON. Read by stage.html and settings.js. */
window.SPRITES_BEHAVIORS = [
  {"key": "avoidFocus", "label": "Keep clear of the focused window", "default": true, "desc": "Drift out from over the window you are working in."},
  {"key": "avoidDockMenu", "label": "Keep clear of Dock and menu bar", "default": true, "desc": "Extra margin around the Dock, menu-bar icons and banners."},
  {"key": "fullScreenFade", "label": "Fade away in full screen", "default": true, "desc": "Fade out on a full-screen Space; return when you leave it."},
  {"key": "edgeWhileTyping", "label": "Step aside while you type", "default": true, "desc": "Ease to the margins while you type or scroll."},
  {"key": "perch", "label": "Perch on window edges", "default": true, "desc": "Idle sprites sometimes rest on the top edge of a background window."},
  {"key": "followOwnWindow", "label": "Stay near their own terminal", "default": true, "desc": "Each sprite hangs near its own session's window."},
  {"key": "avoidCursor", "label": "Keep clear of the cursor", "default": true, "desc": "Gently move away from the pointer."},
  {"key": "curiosity", "label": "Show curiosity", "default": true, "desc": "Drift a little toward a resting cursor, then lose interest."},
  {"key": "hoverName", "label": "Show name on hover", "default": true, "desc": "Slow down and show the project name when the cursor is near."},
  {"key": "sleepWhenAway", "label": "Sleep when you are away", "default": true, "desc": "Slow right down after minutes of no input; wake softly when you return."},
  {"key": "needsApproach", "label": "Come closer when you are needed", "default": true, "desc": "A sprite that needs you edges toward your focus."},
  {"key": "nudgeLongWait", "label": "Edge closer on long waits", "default": true, "desc": "After 10 minutes waiting, creep a little nearer, never touching."},
  {"key": "vpnHuddle", "label": "Huddle when the VPN drops", "default": true, "desc": "Sprites gather together when the connection is lost."},
  {"key": "strainAgitation", "label": "Show machine strain", "default": true, "desc": "Sprites grow restless when the machine is under load."},
  {"key": "quietUnderStrain", "label": "Go quiet under strain", "default": true, "desc": "Skip the finished-work flourish while the machine is under heavy strain."},
  {"key": "play", "label": "Play occasionally", "default": true, "desc": "Idle sprites sometimes interact with one another."},
  {"key": "greetNewcomers", "label": "Greet newcomers", "default": true, "desc": "A nearby sprite drifts briefly toward a new session."},
  {"key": "celebrateDone", "label": "Celebrate finished work", "default": true, "desc": "One small flourish when a session completes."},
  {"key": "arrivals", "label": "Arrivals and departures", "default": true, "desc": "Sprites fade in and out as sessions start and end."}
];
