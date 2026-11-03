import AppKit
import Accelerate
import CoreGraphics
import CoreText
import JavaScriptCore

/// Core Graphics interpreter for app/native/cmdrec.js's op arrays (the hover labels; docs/NATIVE_PORT.md "Labels").
/// The op format and the `__native.cg` host call are documented at the top of cmdrec.js. Canvas semantics kept here:
/// shadows and filter blur are Gaussian in device px (shadow sigma = shadowBlur / 2, as Blink), filter before shadow,
/// shadow then shape each composited with the current operation; source-in/out, destination-in/atop and copy are
/// unbounded (they clear outside the shape, inside the clip); gradients pad, interpolating unpremultiplied; text is
/// glyph outlines from CoreText (CSS font matching, synthetic italic and bold as Blink/Skia), letter spacing after every
/// character. Not thread-safe: call from one thread (the main thread in the app).
enum CGCanvas {
    /// Test hook: family names to treat as unavailable (headless Chromium has no `ui-rounded`; the app's WebKit does).
    static var skipFamilies: Set<String> = []

    /// Rasterize `ops` into a box of `width` x `height` CSS px whose top-left is (originX, originY) in the ops' CSS space.
    /// The image is round(width * scale) x round(height * scale) px, premultiplied RGBA8, sRGB, row 0 at the top.
    static func render(ops: [Any], width: Int, height: Int, scale: CGFloat, originX: CGFloat, originY: CGFloat) -> CGImage? {
        let w = max(1, Int((CGFloat(width) * scale).rounded())), h = max(1, Int((CGFloat(height) * scale).rounded()))
        guard let c = Bitmap.make(w, h) else { return nil }
        let it = Interp(ctx: c, w: w, h: h, scale: scale, origin: CGPoint(x: originX, y: originY))
        it.run(ops)
        return c.makeImage()
    }
    /// The same, from cmdrec.js's `json` string.
    static func render(json: String, width: Int, height: Int, scale: CGFloat, originX: CGFloat, originY: CGFloat) -> CGImage? {
        guard let a = (try? JSONSerialization.jsonObject(with: Data(json.utf8))) as? [Any] else { return nil }
        return render(ops: a, width: width, height: height, scale: scale, originX: originX, originY: originY)
    }

    /// Text metrics for cmdrec.js (keys documented there), CSS px.
    static func measure(font css: String, text: String) -> [String: Double] {
        let f = Fonts.resolve(css), g = Glyphs.layout(text, f, spacing: 0)
        let b = g.path.isEmpty ? CGRect.zero : g.path.boundingBoxOfPath
        let asc = CTFontGetAscent(f.font), desc = CTFontGetDescent(f.font), ea = asc / max(1e-6, asc + desc) * f.px
        // glyph path is y-down: ascent above the baseline = -minY
        return ["w": Double(g.advance), "l": Double(-b.minX), "r": Double(b.maxX), "a": Double(-b.minY), "d": Double(b.maxY),
                "fa": Double(asc.rounded()), "fd": Double(desc.rounded()), "ea": Double(ea), "ed": Double(f.px - ea), "hg": Double(asc * 0.8)]
    }

    /// getImageData for cmdrec.js: the rectangle (x, y, w, h) of offscreen canvas `key` as unpremultiplied RGBA8.
    static func pixels(defs: [Any], key: String, x: Int, y: Int, w: Int, h: Int) -> [UInt8]? {
        Interp.register(defs)
        guard let d = Defs.table[key] else { return nil }
        var out = [UInt8](repeating: 0, count: max(0, w * h * 4))
        guard let img = Defs.image(key), let data = img.dataProvider?.data, let p = CFDataGetBytePtr(data) else { return out }
        let bpr = img.bytesPerRow
        for yy in 0..<h { let sy = y + yy; if sy < 0 || sy >= d.h { continue }
            for xx in 0..<w { let sx = x + xx; if sx < 0 || sx >= d.w { continue }
                let s = sy * bpr + sx * 4, o = (yy * w + xx) * 4, a = Int(p[s + 3])
                if a == 0 { continue }
                for k in 0..<3 { out[o + k] = UInt8(min(255, (Int(p[s + k]) * 255 + a / 2) / a)) }
                out[o + 3] = UInt8(a) } }
        return out
    }

    /// Installs `cg(request, out)` on the host object (`__native`), as cmdrec.js expects.
    static func install(into native: JSValue) {
        let cg: @convention(block) (String, JSValue) -> String = { req, out in
            guard let o = (try? JSONSerialization.jsonObject(with: Data(req.utf8))) as? [String: Any], let q = o["q"] as? String else { return "error: bad request" }
            switch q {
            case "measure":
                let m = measure(font: o["font"] as? String ?? "10px sans-serif", text: o["text"] as? String ?? "")
                guard let j = try? JSONSerialization.data(withJSONObject: m) else { return "error: json" }
                return String(decoding: j, as: UTF8.self)
            case "pixels":
                let n = { (k: String) in (o[k] as? NSNumber)?.intValue ?? 0 }
                guard let key = o["key"] as? String, let px = pixels(defs: o["ops"] as? [Any] ?? [], key: key, x: n("x"), y: n("y"), w: n("w"), h: n("h")) else { return "error: unknown canvas" }
                guard let ctx = JSContext.current(), let ref = out.jsValueRef else { return "error: no buffer" }
                var ex: JSValueRef? = nil
                guard let p = JSObjectGetTypedArrayBytesPtr(ctx.jsGlobalContextRef, ref, &ex) else { return "error: not a typed array" }
                let len = JSObjectGetTypedArrayByteLength(ctx.jsGlobalContextRef, ref, &ex)
                _ = px.withUnsafeBytes { b in memcpy(p, b.baseAddress!, min(len, b.count)) }
                return "ok"
            default: return "error: unknown query \(q)"
            }
        }
        native.setObject(cg, forKeyedSubscript: "cg" as NSString)
    }
}

// MARK: - bitmaps

private enum Bitmap {
    static let space = CGColorSpace(name: CGColorSpace.sRGB)!
    /// Premultiplied RGBA8, y-down user space with the origin at the top-left pixel.
    static func make(_ w: Int, _ h: Int) -> CGContext? {
        guard let c = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4, space: space,
                                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue | CGBitmapInfo.byteOrder32Big.rawValue) else { return nil }
        c.translateBy(x: 0, y: CGFloat(h)); c.scaleBy(x: 1, y: -1)
        c.setShouldAntialias(true); c.setAllowsAntialiasing(true)
        return c
    }
    /// Draw `img` with its top-left at `r.origin` in a y-down user space.
    static func draw(_ img: CGImage, in r: CGRect, on c: CGContext) {
        c.saveGState(); c.translateBy(x: r.minX, y: r.maxY); c.scaleBy(x: 1, y: -1)
        c.draw(img, in: CGRect(x: 0, y: 0, width: r.width, height: r.height)); c.restoreGState()
    }
}

/// Separable Gaussian blur of a premultiplied RGBA8 bitmap (all four channels alike).
private enum Blur {
    static func kernel(_ sigma: CGFloat) -> [Int16] {
        let r = max(1, Int(ceil(sigma * 3))); var k = [Double](repeating: 0, count: 2 * r + 1)
        for i in -r...r { k[i + r] = exp(-Double(i * i) / (2 * Double(sigma * sigma))) }
        let s = k.reduce(0, +); return k.map { Int16(($0 / s * 16384).rounded()) }
    }
    static func apply(_ c: CGContext, sigma: CGFloat) {
        guard sigma > 0.05, let data = c.data else { return }
        let w = c.width, h = c.height, bpr = c.bytesPerRow
        let k = kernel(sigma), div = Int32(k.reduce(0) { $0 + Int32($1) })
        var src = vImage_Buffer(data: data, height: vImagePixelCount(h), width: vImagePixelCount(w), rowBytes: bpr)
        guard let tmp = malloc(bpr * h) else { return }; defer { free(tmp) }
        var dst = vImage_Buffer(data: tmp, height: vImagePixelCount(h), width: vImagePixelCount(w), rowBytes: bpr)
        var bg: [UInt8] = [0, 0, 0, 0]
        k.withUnsafeBufferPointer { kp in
            _ = vImageConvolve_ARGB8888(&src, &dst, nil, 0, 0, kp.baseAddress!, 1, UInt32(k.count), div, &bg, vImage_Flags(kvImageBackgroundColorFill))
            _ = vImageConvolve_ARGB8888(&dst, &src, nil, 0, 0, kp.baseAddress!, UInt32(k.count), 1, div, &bg, vImage_Flags(kvImageBackgroundColorFill))
        }
    }
}

// MARK: - fonts and text

struct ResolvedFont { let font: CTFont; let px: CGFloat; let italic: Bool; let bold: Bool }

private enum Fonts {
    static var cache: [String: ResolvedFont] = [:]
    static let cssWeights: [(CGFloat, CGFloat)] = [(-0.8, 100), (-0.6, 200), (-0.4, 300), (0, 400), (0.23, 500), (0.3, 600), (0.4, 700), (0.56, 800), (0.62, 900)]
    static func cssWeight(_ t: CGFloat) -> CGFloat {
        if t <= cssWeights[0].0 { return 100 }; if t >= cssWeights.last!.0 { return 900 }
        for i in 0..<(cssWeights.count - 1) { let (a, wa) = cssWeights[i], (b, wb) = cssWeights[i + 1]
            if t >= a && t <= b { return wa + (wb - wa) * (t - a) / max(1e-6, b - a) } }
        return 400
    }
    static func nsWeight(_ w: CGFloat) -> NSFont.Weight {
        if w <= 100 { return .ultraLight }; if w >= 900 { return .black }
        for i in 0..<(cssWeights.count - 1) { let (a, wa) = cssWeights[i], (b, wb) = cssWeights[i + 1]
            if w >= wa && w <= wb { return NSFont.Weight(rawValue: a + (b - a) * (w - wa) / (wb - wa)) } }
        return .regular
    }

    /// CSS font shorthand: [style] [variant] [weight] [stretch] size[/line-height] family[, family...]
    static func parse(_ css: String) -> (italic: Bool, weight: CGFloat, px: CGFloat, families: [String]) {
        var italic = false, weight: CGFloat = 400, px: CGFloat = 10, fams: [String] = []
        let s = css.trimmingCharacters(in: .whitespaces)
        let re = try! NSRegularExpression(pattern: "(^|\\s)([0-9.]+)(px|pt|em|rem|%)(\\s*/\\s*\\S+)?\\s+")
        guard let m = re.firstMatch(in: s, range: NSRange(s.startIndex..., in: s)),
              let pre = Range(NSRange(location: 0, length: m.range(at: 2).location), in: s),
              let num = Range(m.range(at: 2), in: s), let all = Range(m.range, in: s) else { return (false, 400, 10, ["sans-serif"]) }
        for t in s[pre].split(separator: " ").map({ $0.lowercased() }) {
            switch t {
            case "italic", "oblique": italic = true
            case "bold": weight = 700
            case "bolder": weight = 700
            case "lighter": weight = 300
            default: if let v = Double(t), v >= 1, v <= 1000 { weight = CGFloat(v) }
            }
        }
        let v = CGFloat(Double(s[num]) ?? 10), u = m.range(at: 3).location != NSNotFound ? String(s[Range(m.range(at: 3), in: s)!]) : "px"
        px = u == "pt" ? v * 4 / 3 : (u == "em" || u == "rem") ? v * 16 : u == "%" ? v / 100 * 16 : v
        fams = s[all.upperBound...].split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces).trimmingCharacters(in: CharacterSet(charactersIn: "'\"")) }.filter { !$0.isEmpty }
        return (italic, weight, px, fams.isEmpty ? ["sans-serif"] : fams)
    }

    static func resolve(_ css: String) -> ResolvedFont {
        if let f = cache[css] { return f }
        let p = parse(css)
        var out: ResolvedFont? = nil
        for fam in p.families where !CGCanvas.skipFamilies.contains(fam) {
            if let f = family(fam, italic: p.italic, weight: p.weight, px: p.px) { out = f; break }
        }
        let f = out ?? family("Times", italic: p.italic, weight: p.weight, px: p.px)!
        if cache.count > 256 { cache.removeAll() }
        cache[css] = f; return f
    }

    static func system(_ design: NSFontDescriptor.SystemDesign, italic: Bool, weight: CGFloat, px: CGFloat) -> ResolvedFont? {
        var d = NSFont.systemFont(ofSize: px, weight: nsWeight(weight)).fontDescriptor
        if design != .default { guard let dd = d.withDesign(design) else { return nil }; d = dd }
        var synthItalic = italic
        if italic { let di = d.withSymbolicTraits(d.symbolicTraits.union(.italic)); if di.symbolicTraits.contains(.italic) { d = di; synthItalic = false } }
        guard let f = NSFont(descriptor: d, size: px) else { return nil }
        if italic && synthItalic && (CTFontGetSymbolicTraits(f as CTFont).contains(.traitItalic)) { synthItalic = false }
        return ResolvedFont(font: f as CTFont, px: px, italic: synthItalic, bold: false)
    }

    static func family(_ name: String, italic: Bool, weight: CGFloat, px: CGFloat) -> ResolvedFont? {
        switch name.lowercased() {
        case "system-ui", "-apple-system", "blinkmacsystemfont", "ui-sans-serif": return system(.default, italic: italic, weight: weight, px: px)
        case "ui-rounded": return system(.rounded, italic: italic, weight: weight, px: px)
        case "ui-serif": return system(.serif, italic: italic, weight: weight, px: px)
        case "ui-monospace": return system(.monospaced, italic: italic, weight: weight, px: px)
        case "serif": return family("Times", italic: italic, weight: weight, px: px)
        case "sans-serif": return family("Helvetica", italic: italic, weight: weight, px: px)
        case "cursive": return family("Apple Chancery", italic: italic, weight: weight, px: px)
        case "fantasy": return family("Papyrus", italic: italic, weight: weight, px: px)
        case "monospace": return family("Courier", italic: italic, weight: weight, px: px)
        default: break
        }
        let d = CTFontDescriptorCreateWithAttributes([kCTFontFamilyNameAttribute: name] as CFDictionary)
        guard let faces = CTFontDescriptorCreateMatchingFontDescriptors(d, nil) as? [CTFontDescriptor], !faces.isEmpty else { return nil }
        // CSS font matching: style first (italic/oblique faces, else normal), then weight
        struct Face { let d: CTFontDescriptor; let italic: Bool; let w: CGFloat }
        var all: [Face] = []
        for f in faces {
            let tr = CTFontDescriptorCopyAttribute(f, kCTFontTraitsAttribute) as? [String: Any] ?? [:]
            let sym = (tr[kCTFontSymbolicTrait as String] as? NSNumber)?.uint32Value ?? 0
            let wt = CGFloat((tr[kCTFontWeightTrait as String] as? NSNumber)?.doubleValue ?? 0)
            let slant = CGFloat((tr[kCTFontSlantTrait as String] as? NSNumber)?.doubleValue ?? 0)
            let style = (CTFontDescriptorCopyAttribute(f, kCTFontStyleNameAttribute) as? String ?? "").lowercased()
            if style.contains("ornament") { continue }
            all.append(Face(d: f, italic: sym & CTFontSymbolicTraits.traitItalic.rawValue != 0 || slant > 0.02, w: cssWeight(wt)))
        }
        if all.isEmpty { return nil }
        var pool = all.filter { $0.italic == italic }; if pool.isEmpty { pool = all }
        let want = weight
        func pick(_ p: [Face]) -> Face {
            if let e = p.first(where: { abs($0.w - want) < 1 }) { return e }
            let up = p.filter { $0.w > want }.sorted { $0.w < $1.w }, dn = p.filter { $0.w < want }.sorted { $0.w > $1.w }
            if want >= 400 && want <= 500 {
                if let m = p.filter({ $0.w > want && $0.w <= 500 }).sorted(by: { $0.w < $1.w }).first { return m }
                return dn.first ?? up.first! }
            if want > 500 { return up.first ?? dn.first! }
            return dn.first ?? up.first!
        }
        let face = pick(pool)
        let font = CTFontCreateWithFontDescriptor(face.d, px, nil)
        let synthItalic = italic && !face.italic
        let synthBold = want >= 600 && face.w < 600 - 1e-3 && face.w <= 500
        return ResolvedFont(font: font, px: px, italic: synthItalic, bold: synthBold)
    }
}

private enum Glyphs {
    struct Run { let font: CTFont; let glyphs: [CGGlyph]; let pos: [CGPoint] }   // pos: user space, y down, baseline 0
    struct Layout { let path: CGPath; let advance: CGFloat; let runs: [Run]; let italic: Bool; let bold: CGFloat }
    static var cache: [String: Layout] = [:]
    /// Glyph outlines of `text` in user space, y down, alphabetic baseline at y = 0, starting at x = 0.
    static func layout(_ text: String, _ f: ResolvedFont, spacing ls: CGFloat) -> Layout {
        let key = "\(CTFontCopyPostScriptName(f.font))|\(f.px)|\(f.italic)|\(f.bold)|\(ls)|\(text)"
        if let l = cache[key] { return l }
        var attrs: [NSAttributedString.Key: Any] = [NSAttributedString.Key(kCTFontAttributeName as String): f.font]
        if ls != 0 { attrs[NSAttributedString.Key(kCTLigatureAttributeName as String)] = 0 }
        let line = CTLineCreateWithAttributedString(NSAttributedString(string: text, attributes: attrs))
        let adv = CGFloat(CTLineGetTypographicBounds(line, nil, nil, nil))
        let path = CGMutablePath()
        var runs: [Run] = []
        let chars = Array(text.utf16)
        // character index (UTF-16 offset) -> count of characters (grapheme-ish: code points) before it
        var cpBefore = [Int](repeating: 0, count: chars.count + 1); var n = 0
        for i in 0..<chars.count { cpBefore[i] = n; if !(0xDC00...0xDFFF).contains(chars[i]) { n += 1 } }
        cpBefore[chars.count] = n
        for run in (CTLineGetGlyphRuns(line) as? [CTRun]) ?? [] {
            let cnt = CTRunGetGlyphCount(run); if cnt == 0 { continue }
            let ra = CTRunGetAttributes(run) as NSDictionary
            let rf = (ra[kCTFontAttributeName as String] as! CTFont)
            var gl = [CGGlyph](repeating: 0, count: cnt), pos = [CGPoint](repeating: .zero, count: cnt), idx = [CFIndex](repeating: 0, count: cnt)
            CTRunGetGlyphs(run, CFRange(location: 0, length: cnt), &gl)
            CTRunGetPositions(run, CFRange(location: 0, length: cnt), &pos)
            CTRunGetStringIndices(run, CFRange(location: 0, length: cnt), &idx)
            var up: [CGPoint] = []
            for i in 0..<cnt {
                let off = ls * CGFloat(cpBefore[min(chars.count, max(0, idx[i]))])
                var m = CGAffineTransform(a: 1, b: 0, c: f.italic ? 0.25 : 0, d: -1, tx: pos[i].x + off, ty: -pos[i].y)
                up.append(CGPoint(x: pos[i].x + off, y: -pos[i].y))
                if let gp = CTFontCreatePathForGlyph(rf, gl[i], &m) { path.addPath(gp) }
            }
            runs.append(Run(font: rf, glyphs: gl, pos: up))
        }
        var out: CGPath = path, extra: CGFloat = 0
        if f.bold && !path.isEmpty {   // Skia's fake bold: outline grown by size * (1/24 at 9 px .. 1/32 at 36 px)
            let t = min(1, max(0, (f.px - 9) / 27)); extra = f.px * (1.0 / 24 + (1.0 / 32 - 1.0 / 24) * t)
            let stroked = path.copy(strokingWithWidth: extra, lineCap: .butt, lineJoin: .miter, miterLimit: 4)
            out = path.union(stroked, using: .winding)
        }
        let l = Layout(path: out, advance: adv, runs: runs, italic: f.italic, bold: extra)
        if cache.count > 2048 { cache.removeAll() }
        cache[key] = l; return l
    }
}

// MARK: - offscreen canvas definitions

private enum Defs {
    struct Def { let w: Int; let h: Int; let ops: [Any] }
    static var table: [String: Def] = [:]
    static var images: [String: CGImage] = [:]
    static var order: [String] = []
    static func define(_ key: String, _ d: Def) {
        if table[key] != nil { return }
        table[key] = d; order.append(key)
        if order.count > 256 { let k = order.removeFirst(); table.removeValue(forKey: k); images.removeValue(forKey: k) }
    }
    static func image(_ key: String) -> CGImage? {
        if let i = images[key] { return i }
        guard let d = table[key], d.w > 0, d.h > 0, let c = Bitmap.make(d.w, d.h) else { return nil }
        Interp(ctx: c, w: d.w, h: d.h, scale: 1, origin: .zero).run(d.ops)
        let i = c.makeImage(); images[key] = i; return i
    }
}

// MARK: - the interpreter

private enum Paint {
    case solid(CGColor)
    case linear(CGGradient, CGPoint, CGPoint)
    case radial(CGGradient, CGPoint, CGFloat, CGPoint, CGFloat)
}

private final class Interp {
    struct State {
        var m = CGAffineTransform.identity
        var alpha: CGFloat = 1
        var comp = "source-over"
        var fill = Paint.solid(CGColor(srgbRed: 0, green: 0, blue: 0, alpha: 1))
        var stroke = Paint.solid(CGColor(srgbRed: 0, green: 0, blue: 0, alpha: 1))
        var lw: CGFloat = 1, cap = CGLineCap.butt, join = CGLineJoin.miter, miter: CGFloat = 10
        var shBlur: CGFloat = 0, shX: CGFloat = 0, shY: CGFloat = 0, shC: [CGFloat] = [0, 0, 0, 0]
        var fsig: CGFloat = 0
        var font = "10px sans-serif", ls: CGFloat = 0
        var smooth = true, quality = "low"
    }
    let c: CGContext, w: Int, h: Int, scale: CGFloat, base: CGAffineTransform
    var st = State(), stack: [State] = []
    var path = CGMutablePath()   // current path, CSS space

    init(ctx: CGContext, w: Int, h: Int, scale: CGFloat, origin: CGPoint) {
        c = ctx; self.w = w; self.h = h; self.scale = scale
        base = CGAffineTransform(a: scale, b: 0, c: 0, d: scale, tx: -origin.x * scale, ty: -origin.y * scale)
        c.concatenate(base)
    }

    static func register(_ ops: [Any]) {
        var i = 0
        while i < ops.count { guard let op = ops[i] as? String else { i += 1; continue }
            if op == "D", i + 4 < ops.count, let k = ops[i + 1] as? String, let sub = ops[i + 4] as? [Any] {
                Defs.define(k, Defs.Def(w: (ops[i + 2] as? NSNumber)?.intValue ?? 0, h: (ops[i + 3] as? NSNumber)?.intValue ?? 0, ops: sub)); i += 5 }
            else { i += 1 } }
    }

    // op argument readers
    private var ops: [Any] = [], i = 0
    private func n() -> CGFloat { defer { i += 1 }; return i < ops.count ? CGFloat((ops[i] as? NSNumber)?.doubleValue ?? 0) : 0 }
    private func s() -> String { defer { i += 1 }; return i < ops.count ? (ops[i] as? String ?? "") : "" }
    private func a() -> [Any] { defer { i += 1 }; return i < ops.count ? (ops[i] as? [Any] ?? []) : [] }

    func run(_ list: [Any]) {
        let saveOps = ops, saveI = i; ops = list; i = 0
        defer { ops = saveOps; i = saveI }
        while i < ops.count {
            guard let op = ops[i] as? String else { i += 1; continue }
            i += 1
            switch op {
            case "s": stack.append(st); c.saveGState()
            case "r": if let p = stack.popLast() { st = p; c.restoreGState() }
            case "M": st.m = CGAffineTransform(a: n(), b: n(), c: n(), d: n(), tx: n(), ty: n())
            case "A": st.alpha = n()
            case "C": st.comp = s()
            case "IS": st.smooth = n() != 0
            case "IQ": st.quality = s()
            case "F": st.fill = paint()
            case "S": st.stroke = paint()
            case "W": st.lw = n()
            case "LC": switch s() { case "round": st.cap = .round; case "square": st.cap = .square; default: st.cap = .butt }
            case "LJ": switch s() { case "round": st.join = .round; case "bevel": st.join = .bevel; default: st.join = .miter }
            case "ML": st.miter = n()
            case "SH": st.shBlur = n(); st.shX = n(); st.shY = n(); st.shC = [n(), n(), n(), n()]
            case "FI": st.fsig = n()
            case "FN": st.font = s()
            case "LS": st.ls = n()
            case "P": path = Interp.path(a())
            case "f": let rule: CGPathFillRule = s() == "evenodd" ? .evenOdd : .winding; fill(path, rule)
            case "k": strokeCSS(path)
            case "c": let rule: CGPathFillRule = s() == "evenodd" ? .evenOdd : .winding
                c.addPath(path); c.clip(using: rule)
            case "X": c.saveGState(); c.setBlendMode(.clear); c.addPath(path); c.fillPath(); c.restoreGState()
            case "T": let mode = Int(n()), str = s(), x = n(), y = n(), sx = n(); self.text(mode, str, x, y, sx)
            case "I": let key = s(); let r = [n(), n(), n(), n(), n(), n(), n(), n()]; image(key, r)
            case "D": let k = s(), dw = Int(n()), dh = Int(n()), sub = a(); Defs.define(k, Defs.Def(w: dw, h: dh, ops: sub))
            default: break
            }
        }
    }

    private func paint() -> Paint {
        let t = Int(n())
        if t == 0 { return .solid(CGColor(srgbRed: n(), green: n(), blue: n(), alpha: n())) }
        let g = (0..<(t == 1 ? 4 : 6)).map { _ in n() }, cnt = Int(n())
        var locs: [CGFloat] = [], cols: [CGFloat] = []
        for _ in 0..<cnt { locs.append(n()); cols += [n(), n(), n(), n()] }
        if cnt == 0 { return .solid(CGColor(srgbRed: 0, green: 0, blue: 0, alpha: 0)) }
        let grad = CGGradient(colorSpace: Bitmap.space, colorComponents: cols, locations: locs, count: cnt)!
        return t == 1 ? .linear(grad, CGPoint(x: g[0], y: g[1]), CGPoint(x: g[2], y: g[3]))
                      : .radial(grad, CGPoint(x: g[0], y: g[1]), g[2], CGPoint(x: g[3], y: g[4]), g[5])
    }

    static func path(_ a: [Any]) -> CGMutablePath {
        let p = CGMutablePath(); var i = 0
        func v() -> CGFloat { defer { i += 1 }; return i < a.count ? CGFloat((a[i] as? NSNumber)?.doubleValue ?? 0) : 0 }
        while i < a.count {
            let k = Int(v())
            switch k {
            case 0: p.move(to: CGPoint(x: v(), y: v()))
            case 1: let q = CGPoint(x: v(), y: v()); if p.isEmpty { p.move(to: q) } else { p.addLine(to: q) }
            case 2: let c1 = CGPoint(x: v(), y: v()), e = CGPoint(x: v(), y: v()); p.addQuadCurve(to: e, control: c1)
            case 3: let c1 = CGPoint(x: v(), y: v()), c2 = CGPoint(x: v(), y: v()), e = CGPoint(x: v(), y: v()); p.addCurve(to: e, control1: c1, control2: c2)
            case 4: p.closeSubpath()
            default: return p
            }
        }
        return p
    }

    // ----- composition: one draw, with filter, shadow, alpha and the composite operation -----
    private static let blend: [String: CGBlendMode] = ["source-over": .normal, "lighter": .plusLighter, "source-in": .sourceIn,
        "source-out": .sourceOut, "source-atop": .sourceAtop, "destination-over": .destinationOver, "destination-in": .destinationIn,
        "destination-out": .destinationOut, "destination-atop": .destinationAtop, "copy": .copy, "xor": .xor, "multiply": .multiply,
        "screen": .screen, "overlay": .overlay, "darken": .darken, "lighten": .lighten, "color-dodge": .colorDodge, "color-burn": .colorBurn,
        "hard-light": .hardLight, "soft-light": .softLight, "difference": .difference, "exclusion": .exclusion, "hue": .hue,
        "saturation": .saturation, "color": .color, "luminosity": .luminosity]
    private static let unbounded: Set<String> = ["source-in", "source-out", "destination-in", "destination-atop", "copy"]

    /// `draw` paints the shape (without alpha or blend) into a context whose CTM maps CSS space to its pixels.
    /// `box` is the shape's CSS-space bounds (stroke included).
    private func emit(_ box: CGRect, _ draw: (CGContext) -> Void) {
        let mode = Interp.blend[st.comp] ?? .normal, unb = Interp.unbounded.contains(st.comp)
        let hasShadow = st.shC[3] > 0 && (st.shBlur > 0 || st.shX != 0 || st.shY != 0)
        let fsig = st.fsig * scale, ssig = st.shBlur * scale / 2
        if fsig <= 0.05 && !hasShadow && !unb {
            c.saveGState(); c.setAlpha(st.alpha); c.setBlendMode(mode); draw(c); c.restoreGState(); return }
        let full = CGRect(x: 0, y: 0, width: w, height: h)
        var r = box.applying(base).insetBy(dx: -(3 * fsig + 2), dy: -(3 * fsig + 2))
        let sdx = st.shX * scale, sdy = st.shY * scale
        if hasShadow { r = r.union(r.offsetBy(dx: -sdx, dy: -sdy).insetBy(dx: -3 * ssig - 2, dy: -3 * ssig - 2)) }
        r = unb ? full : r.integral.intersection(full)
        if r.isNull || r.width < 1 || r.height < 1 { return }
        let lw = Int(r.width), lh = Int(r.height)
        guard let L = Bitmap.make(lw, lh) else { return }
        L.translateBy(x: -r.minX, y: -r.minY); L.concatenate(base)
        draw(L)
        if fsig > 0.05 { Blur.apply(L, sigma: fsig) }
        guard let shape = L.makeImage() else { return }
        c.saveGState(); c.concatenate(base.inverted()); c.setAlpha(st.alpha); c.setBlendMode(mode); c.interpolationQuality = .none
        if hasShadow, let S = Bitmap.make(lw, lh) {
            // the shape's alpha, blurred, in the shadow colour
            S.saveGState(); S.translateBy(x: 0, y: CGFloat(lh)); S.scaleBy(x: 1, y: -1)
            S.clip(to: CGRect(x: 0, y: 0, width: lw, height: lh), mask: shape)
            S.setFillColor(CGColor(srgbRed: st.shC[0], green: st.shC[1], blue: st.shC[2], alpha: st.shC[3]))
            S.fill(CGRect(x: 0, y: 0, width: lw, height: lh)); S.restoreGState()
            Blur.apply(S, sigma: ssig)
            if let si = S.makeImage() { Bitmap.draw(si, in: CGRect(x: r.minX + sdx, y: r.minY + sdy, width: CGFloat(lw), height: CGFloat(lh)), on: c) }
        }
        Bitmap.draw(shape, in: CGRect(x: r.minX, y: r.minY, width: CGFloat(lw), height: CGFloat(lh)), on: c)
        c.restoreGState()
    }

    /// Fill `p` (already in the context's current space) with a paint whose geometry is in user space under `m`.
    private func paintPath(_ g: CGContext, _ p: CGPath, _ rule: CGPathFillRule, _ pt: Paint, _ m: CGAffineTransform) {
        g.saveGState(); g.addPath(p)
        switch pt {
        case .solid(let col): g.setFillColor(col); g.fillPath(using: rule)
        case .linear(let gr, let a, let b): g.clip(using: rule); g.concatenate(m)
            g.drawLinearGradient(gr, start: a, end: b, options: [.drawsBeforeStartLocation, .drawsAfterEndLocation])
        case .radial(let gr, let a, let ra, let b, let rb): g.clip(using: rule); g.concatenate(m)
            g.drawRadialGradient(gr, startCenter: a, startRadius: ra, endCenter: b, endRadius: rb, options: [.drawsBeforeStartLocation, .drawsAfterEndLocation])
        }
        g.restoreGState()
    }
    private func paintIsVisible(_ pt: Paint) -> Bool { if case .solid(let col) = pt { return col.alpha > 0 }; return true }

    private func fill(_ p: CGPath, _ rule: CGPathFillRule) {
        if p.isEmpty || !paintIsVisible(st.fill) { return }
        let pt = st.fill, m = st.m
        emit(p.boundingBoxOfPath) { g in self.paintPath(g, p, rule, pt, m) }
    }
    /// Stroke a user-space path under the current transform.
    private func strokeUser(_ up: CGPath) {
        if up.isEmpty || !paintIsVisible(st.stroke) { return }
        let m = st.m, outline = up.copy(strokingWithWidth: st.lw, lineCap: st.cap, lineJoin: st.join, miterLimit: st.miter)
        var mm = m; guard let css = outline.copy(using: &mm) else { return }
        let pt = st.stroke
        emit(css.boundingBoxOfPath) { g in self.paintPath(g, css, .winding, pt, m) }
    }
    private func strokeCSS(_ p: CGPath) {
        var inv = st.m.inverted(); if st.m.a * st.m.d - st.m.b * st.m.c == 0 { return }
        guard let up = p.copy(using: &inv) else { return }
        strokeUser(up)
    }
    private func text(_ mode: Int, _ text: String, _ x: CGFloat, _ y: CGFloat, _ sx: CGFloat) {
        let f = Fonts.resolve(st.font), g = Glyphs.layout(text, f, spacing: st.ls)
        var t = CGAffineTransform(a: sx, b: 0, c: 0, d: 1, tx: x, ty: y)
        guard let up = g.path.copy(using: &t) else { return }
        if mode == 1 { strokeUser(up); return }
        var m = st.m; guard let css = up.copy(using: &m) else { return }
        if Interp.pathText || css.isEmpty || !paintIsVisible(st.fill) { fill(css, .winding); return }
        // Skia (Chromium) rasterizes glyph masks with CoreGraphics font smoothing, black on white, then uses the inverse as
        // coverage; that is heavier than a plain path fill. Do the same: an opaque mask in device px, then paint through it.
        let um = CGAffineTransform(a: sx, b: 0, c: 0, d: 1, tx: x, ty: y).concatenating(st.m), dev = um.concatenating(base)
        let r = css.boundingBoxOfPath.applying(base).insetBy(dx: -2, dy: -2).integral
        guard r.width >= 1, r.height >= 1, r.width * r.height < 16_000_000,
              let mk = CGContext(data: nil, width: Int(r.width), height: Int(r.height), bitsPerComponent: 8, bytesPerRow: Int(r.width) * 4,
                                 space: Bitmap.space, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue | CGBitmapInfo.byteOrder32Big.rawValue)
        else { fill(css, .winding); return }
        mk.setFillColor(CGColor(srgbRed: 1, green: 1, blue: 1, alpha: 1)); mk.fill(CGRect(x: 0, y: 0, width: r.width, height: r.height))
        mk.translateBy(x: 0, y: r.height); mk.scaleBy(x: 1, y: -1); mk.translateBy(x: -r.minX, y: -r.minY); mk.concatenate(dev)
        mk.setAllowsFontSmoothing(true); mk.setShouldSmoothFonts(Interp.smoothText); mk.setAllowsAntialiasing(true); mk.setShouldAntialias(true)
        mk.setAllowsFontSubpixelPositioning(true); mk.setShouldSubpixelPositionFonts(true); mk.setAllowsFontSubpixelQuantization(false); mk.setShouldSubpixelQuantizeFonts(false)
        mk.setFillColor(CGColor(srgbRed: 0, green: 0, blue: 0, alpha: 1))
        if g.bold > 0 { mk.setTextDrawingMode(.fillStroke); mk.setStrokeColor(CGColor(srgbRed: 0, green: 0, blue: 0, alpha: 1)); mk.setLineWidth(g.bold); mk.setLineJoin(.miter) }
        mk.textMatrix = CGAffineTransform(a: 1, b: 0, c: g.italic ? 0.25 : 0, d: -1, tx: 0, ty: 0)
        for run in g.runs { for (gi, p) in zip(run.glyphs, run.pos) { var gl = gi, o = CGPoint.zero
            mk.saveGState(); mk.translateBy(x: p.x, y: p.y); CTFontDrawGlyphs(run.font, &gl, &o, 1, mk); mk.restoreGState() } }
        guard let data = mk.data else { fill(css, .winding); return }
        let W = Int(r.width), H = Int(r.height), bpr = mk.bytesPerRow, px = data.assumingMemoryBound(to: UInt8.self)
        var cov = [UInt8](repeating: 0, count: W * H)
        for yy in 0..<H { for xx in 0..<W { let o = yy * bpr + xx * 4
            let v = (Int(px[o]) + Int(px[o + 1]) + Int(px[o + 2])) / 3; cov[yy * W + xx] = Interp.textLUT[255 - v] } }
        guard let prov = CGDataProvider(data: Data(cov) as CFData),
              let mask = CGImage(maskWidth: W, height: H, bitsPerComponent: 8, bitsPerPixel: 8, bytesPerRow: W, provider: prov, decode: nil, shouldInterpolate: false),
              let alpha = CGImage(width: W, height: H, bitsPerComponent: 8, bitsPerPixel: 8, bytesPerRow: W, space: CGColorSpaceCreateDeviceGray(),
                                  bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.none.rawValue), provider: prov, decode: nil, shouldInterpolate: false, intent: .defaultIntent)
        else { fill(css, .winding); return }
        _ = mask
        let pt = st.fill, base = self.base
        emit(css.boundingBoxOfPath.insetBy(dx: -1, dy: -1)) { gc in
            gc.saveGState(); gc.concatenate(base.inverted())
            // clip(to:mask:) with a gray image uses it as alpha; the rect is y-up inside, so flip around it
            gc.translateBy(x: r.minX, y: r.maxY); gc.scaleBy(x: 1, y: -1); gc.clip(to: CGRect(x: 0, y: 0, width: r.width, height: r.height), mask: alpha)
            gc.scaleBy(x: 1, y: -1); gc.translateBy(x: -r.minX, y: -r.maxY); gc.concatenate(base)
            self.paintPath(gc, CGPath(rect: r.applying(base.inverted()), transform: nil), .winding, pt, m)
            gc.restoreGState() }
    }
    static let pathText = ProcessInfo.processInfo.environment["CG_TEXT_PATH"] == "1"
    static let smoothText = ProcessInfo.processInfo.environment["CG_TEXT_SMOOTH"] != "0"
    static let textLUT: [UInt8] = {
        let g = Double(ProcessInfo.processInfo.environment["CG_TEXT_GAMMA"] ?? "") ?? 1
        return (0..<256).map { UInt8(min(255, (pow(Double($0) / 255, g) * 255).rounded())) } }()
    private func image(_ key: String, _ r: [CGFloat]) {
        guard let d = Defs.table[key], let img = Defs.image(key) else { return }
        var (sx, sy, sw, sh, dx, dy, dw, dh) = (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7])
        if sw < 0 { sx += sw; sw = -sw }; if sh < 0 { sy += sh; sh = -sh }; if dw < 0 { dx += dw; dw = -dw }; if dh < 0 { dy += dh; dh = -dh }
        // clip the source rect to the image, moving the destination with it
        let src = CGRect(x: sx, y: sy, width: sw, height: sh), cl = src.intersection(CGRect(x: 0, y: 0, width: d.w, height: d.h))
        if cl.isNull || cl.width <= 0 || cl.height <= 0 { return }
        let kx = dw / sw, ky = dh / sh
        let dst = CGRect(x: dx + (cl.minX - sx) * kx, y: dy + (cl.minY - sy) * ky, width: cl.width * kx, height: cl.height * ky)
        let piece: CGImage
        if cl.equalTo(CGRect(x: 0, y: 0, width: d.w, height: d.h)) { piece = img } else { guard let p = img.cropping(to: cl.integral) else { return }; piece = p }
        let m = st.m, q: CGInterpolationQuality = !st.smooth ? .none : st.quality == "high" ? .high : .medium
        emit(dst.applying(m)) { g in g.saveGState(); g.concatenate(m); g.interpolationQuality = q; Bitmap.draw(piece, in: dst, on: g); g.restoreGState() }
    }
}
