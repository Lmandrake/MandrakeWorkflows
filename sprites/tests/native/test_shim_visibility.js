// R2_MACOS #8 (native energy, JS half): the native shim's document.hidden is the host's to set. __nativeSetHidden(true)
// sets document.hidden / visibilityState and fires "visibilitychange" once; stage.html's own page-hidden pause then draws
// NO frames (the recording's version stays put over 2 s); __nativeSetHidden(false) fires it again and frames resume.
// Hand-derived: WebKit's page-hidden contract (Page Visibility API). Node only, fake clock (tests/js/harness.js).
"use strict";
const { makeStage, snapshot, check, done } = require("../js/harness.js");
const st = makeStage({ query: "stale=0&vpndebounce=0" });
st.ev(`SpritesStage.setSize(1728,1117); SpritesStage.setCast({projects:{Alpha:{concept:"c5_fireflies",iv:1,hex:"#55aaff"}}})`);
st.ev(`SpritesStage.update(${JSON.stringify(snapshot([{ project: "Alpha" }]))})`); st.fire(); st.step(48);
const ver = () => +st.ev("__nativeVer()");
let v0 = ver(); st.step(24); check(ver() > v0, "frames draw while visible", [v0, ver()]);
check(typeof st.g.__nativeSetHidden === "function", "shim exposes __nativeSetHidden");
let fired = 0; st.ev("document.addEventListener('visibilitychange', () => { globalThis.__vc = (globalThis.__vc || 0) + 1; })");
if (typeof st.g.__nativeSetHidden === "function") {
  st.g.__nativeSetHidden(true); st.g.__nativeSetHidden(true); fired = +st.ev("globalThis.__vc || 0");
  check(st.ev("document.hidden") === true && st.ev("document.visibilityState") === "hidden" && fired === 1, "hidden: document.hidden true, state hidden, one event", [fired]);
  st.step(2); v0 = ver(); st.step(48); check(ver() === v0, "no frames drawn while hidden (2 s)", [v0, ver()]);
  st.g.__nativeSetHidden(false); fired = +st.ev("globalThis.__vc || 0");
  check(st.ev("document.hidden") === false && st.ev("document.visibilityState") === "visible" && fired === 2, "visible again: one more event", [fired]);
  v0 = ver(); st.step(24); check(ver() > v0, "frames resume when visible", [v0, ver()]);
}
done();
