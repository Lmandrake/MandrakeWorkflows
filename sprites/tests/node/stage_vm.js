/* Loads app/stage.html's scripts into a node vm context the way the native host does (app/native/canvas.js + shim.js,
 * then each <script src>, then the inline stage) with a fake clock: nothing renders, no browser, no window.
 * const S = require("./stage_vm")(spritesRoot); S.ctx.SpritesStage...; S.advance(ms) runs the timers due. */
const fs = require("fs"), path = require("path"), vm = require("vm");
module.exports = function load(root, query) {
  let clock = 1e6; const timers = new Map();
  const ctx = { __posts: [] }; ctx.globalThis = ctx; vm.createContext(ctx);
  ctx.__native = { now: () => clock, read: p => { try { return fs.readFileSync(path.join(root, p), "utf8"); } catch (e) { return null; } },
    post: s => ctx.__posts.push(JSON.parse(s)), timer(id, ms, rep) { timers.set(id, { due: clock + ms, ms, rep }); },
    cancel(id) { timers.delete(id); }, log() {}, present() {}, query: query || "stale=0&dpr=1", dpr: 1, w: 1440, h: 900 };
  const run = rel => vm.runInContext(fs.readFileSync(path.join(root, rel), "utf8"), ctx, { filename: rel });
  run("app/native/canvas.js"); run("app/native/shim.js");
  const html = fs.readFileSync(path.join(root, "app/stage.html"), "utf8"), inline = [];
  for (const m of html.matchAll(/<script(?:\s+src="([^"]+)")?[^>]*>([\s\S]*?)<\/script>/g)) {
    if (m[1]) { if (fs.existsSync(path.join(root, "app", m[1]))) run("app/" + m[1]); } else inline.push(m[2]); }
  vm.runInContext(inline[inline.length - 1], ctx, { filename: "app/stage.html" });
  function advance(ms) { const end = clock + ms;
    for (;;) { let id = null, due = Infinity; for (const [k, t] of timers) if (t.due < due) { due = t.due; id = k; }
      if (id === null || due > end) break; clock = due; const t = timers.get(id);
      if (t.rep) t.due = clock + Math.max(4, t.ms); else timers.delete(id); ctx.__nativeFire(id); }
    clock = end; }
  return { ctx, advance };
};
