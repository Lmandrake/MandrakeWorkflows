# Traps by topic

Lessons folded in from the lessons inbox, by the section of `../SKILL.md` they belong to.

## 3. Serve. Serving IS the delivery.
- **A server that "opened the browser" is not proof the human saw the sheet.** The browser may never show it (the human asked for a link). Hand the tokened URL in chat as well, every time.

## 1. Generate. Do not hand-roll the page.
- **A repaint that swaps an INNER node for a render function's output nests whatever wrapper that function adds** (a collapsed `<details>` nested a fresh closed block on every click of an already-ruled row). Repaint the outermost element the renderer emits, and never collapse a row the human is working in or one holding pictures newer than their ruling.
- **A sheet generator derives `decisionsPath`/`sheetPath` from the directory it wrote into, never a literal absolute path.** A literal path to a read-only mirror makes the sheet save decisions to a folder that does not exist.
- **Every hand-written or generated review page carries `<meta name="viewport" content="width=device-width,initial-scale=1">`.** Without it a phone renders about 980 px wide, zoomed out, and every sprite and radio button shrinks. Guard `localStorage.setItem` in change handlers: if storage is blocked, picks still reach the textarea but do not persist.
- **A width the owner names ("read on a 1600 px window") is physical pixels.** At 200% display scale a document column is about 765 CSS px and an inline SVG with viewBox 1040 draws at 0.73; a 1500-wide viewBox shrinks to unreadable. Design at viewBox 1040 with no text under 10.5 units, and test in headless Edge with `--force-device-scale-factor=2 --window-size=825,H`.

## 4. Review: prove the sheet actually wrote
- **When a stored record names both a target and a payload (a slot key and a pick letter), the consumer checks that they agree against the current snapshot and never trusts the UI that wrote them.** A key from an older build installs at a stale path.

## 2. Validate
- **When one gate is enforced at several chokepoints (serve, publish, deliver, commit), every one must read content the same way.** A pre-commit that read the staged blob as raw bytes refused a CRLF sheet that verified everywhere else, because the stamp hash is computed on universal-newline text. A new chokepoint that reads git blobs or bytes normalises them exactly as `read_text` does and is tested with a CRLF fixture.

## 6. Freeze, and make the freeze real
- **A protective guard is an allow-list of the few states that are safe to overwrite (no stamp, a previous blanket ruling), never a deny-list of known bad stamps.** A deny-list fails open on the next stamp someone invents (a blanket-ruling applier refused three sitting `savedBy` values and let another tool's owner-picks stamp through).
