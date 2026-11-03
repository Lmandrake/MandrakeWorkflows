// Sprites backdrops: ONE shader source, compiled twice.
//   Metal (app/macos/Backdrop.swift): typedefs vec2/3/4 -> float2/3/4 are prepended.
//   WebGL2 GLSL ES 3.0 (app/settings.js previews): "#define atan2 atan" is prepended.
// So this file uses only the common subset: scalar clamp/mix, float literals everywhere, no globals,
// no reserved words of either language (sample, half, constant, filter...). Design notes, budgets and the
// reasoning behind each concept: visualize/docs/MACHINE_BACKGROUNDS.md. Python reference generators for
// b01-b10: visualize/backgrounds/. Output of every bgNN(): LINEAR light. p = pixel (top-left origin), res = pixels,
// t = design time in seconds (wall time x the owner's speed setting).
#define PI 3.14159265
#define TAU 6.2831853

float sat(float x) { return clamp(x, 0.0, 1.0); }
vec3 lerp3(vec3 a, vec3 b, float k) { return a + (b - a) * k; }
float s2l(float c) { return c <= 0.04045 ? c / 12.92 : pow((c + 0.055) / 1.055, 2.4); }
float l2s(float c) { c = sat(c); return c <= 0.0031308 ? 12.92 * c : 1.055 * pow(c, 1.0 / 2.4) - 0.055; }
vec3 hexl(float r, float g, float b) { return vec3(s2l(r / 255.0), s2l(g / 255.0), s2l(b / 255.0)); }

// hashes without sine (Hoskins), stable in highp float
float hash12(vec2 p) { vec3 p3 = fract(vec3(p.x, p.y, p.x) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
vec4 hash42(vec2 p) { vec4 p4 = fract(vec4(p.x, p.y, p.x, p.y) * vec4(0.1031, 0.1030, 0.0973, 0.1099));
  p4 += dot(p4, p4.wzxy + 33.33); return fract((p4.xxyz + p4.yzzw) * p4.zywx); }

float vnoise(vec2 x) { vec2 i = floor(x); vec2 f = fract(x); vec2 u = f * f * (3.0 - 2.0 * f);
  float a = hash12(i), b = hash12(i + vec2(1.0, 0.0)), c = hash12(i + vec2(0.0, 1.0)), d = hash12(i + vec2(1.0, 1.0));
  return a + (b - a) * u.x + (c - a) * u.y + (a - b - c + d) * u.x * u.y; }
// fbm rescaled so its spread is close to a single octave's (0..1, mean 0.5)
float fbm(vec2 x, int oct, float gain) { float s = 0.0, a = 1.0, w = 0.0, w2 = 0.0;
  for (int i = 0; i < 6; i++) { if (i >= oct) break; s += a * vnoise(x); w += a; w2 += a * a; a *= gain; x = x * 2.03 + vec2(17.1, 9.7); }
  return 0.5 + (s / w - 0.5) * w / sqrt(w2 * float(oct > 1 ? 2 : 1)) * (oct > 1 ? 1.25 : 1.0); }
// a field that changes shape over time and returns to itself after P seconds (equal variance at every t)
float loopf(vec2 x, float t, float P, int oct, float gain) { float th = TAU * t / P;
  return 0.5 + (fbm(x, oct, gain) - 0.5) * cos(th) + (fbm(x + vec2(71.3, 29.1), oct, gain) - 0.5) * sin(th); }

// one layer of fixed point stars on a jittered grid; returns linear intensity
float starLayer(vec2 p, float cell, float seed, float dens, float sig0, float peakMax) {
  vec2 g = floor(p / cell); float v = 0.0;
  for (int j = -1; j <= 1; j++) { for (int i = -1; i <= 1; i++) {
    vec2 c = g + vec2(float(i), float(j)); vec4 h = hash42(c + vec2(seed, seed * 0.37));
    if (h.x < dens) {
      vec2 sp = (c + 0.15 + 0.7 * h.yz) * cell; float m = pow(1.0 - h.w * 0.999, -1.0 / 2.2);
      float pk = min(0.0016 * pow(m, 1.6), peakMax); float s = max(0.5, (0.55 + 0.35 * fract(h.w * 13.7)) * sig0);
      vec2 d = p - sp; v += pk * exp(-dot(d, d) / (2.0 * s * s)); } } }
  return v; }

// ---------------------------------------------------------------------------------------------------------
vec3 bg01(vec2 p, vec2 res, float t) {   // Abyssal Starfield (static)
  float px = res.y / 2234.0; vec2 u = p / res.y; float asp = res.x / res.y;
  vec3 c = lerp3(hexl(2.0, 3.0, 6.0), hexl(6.0, 9.0, 17.0), 0.15 + 0.6 * u.y * u.y);
  float d = abs((u.x - 0.9 * asp) * 0.5 + (u.y - 0.5)); float band = exp(-(d / 0.35) * (d / 0.35));
  float n = fbm(u * 5.0, 4, 0.5); c += hexl(10.0, 15.0, 26.0) * band * n * n * 0.6;
  float s = starLayer(p, 40.0 * px, 3.0, 0.45 + 0.25 * band, 1.4 * max(px, 0.35), 0.055);
  return c + vec3(0.88, 0.93, 1.0) * s; }

vec3 bg02(vec2 p, vec2 res, float t) {   // Slow Tide
  vec2 u = p / res.y; float asp = res.x / res.y;
  float f = 0.45 * sin(TAU * (0.9 * u.x + 0.35 * u.y) + TAU * t / 660.0)
          + 0.35 * sin(TAU * (-0.45 * u.x + 0.85 * u.y) + TAU * t / 1020.0 + 1.3)
          + 0.25 * sin(TAU * (0.2 * u.x - 0.45 * u.y) + TAU * t / 1380.0 + 4.1);
  f = 0.5 + 0.5 * f / 1.05; float h = loopf(u / 0.9, t, 1740.0, 2, 0.5);
  vec3 lo = lerp3(hexl(3.0, 4.0, 10.0), hexl(2.0, 6.0, 8.0), h), hi = lerp3(hexl(17.0, 18.0, 44.0), hexl(7.0, 26.0, 32.0), h);
  float k = pow(sat(f), 1.6); float vig = 1.0 - 0.35 * ((u.x - asp / 2.0) * (u.x - asp / 2.0) + (u.y - 0.5) * (u.y - 0.5));
  return lerp3(lo, hi, k) * vig; }

vec3 bg03(vec2 p, vec2 res, float t) {   // Threshold Tunnel: rings FIXED; speed turns only the petals and the hue
  vec2 u = p / res.y; vec2 d = u - vec2(res.x / res.y / 2.0, 0.5);
  float r = length(d) + 1e-4, th = atan2(d.y, d.x), lr = log(r);
  float s = 6.0 * lr - 3.0 * th / PI; float twist = TAU * t / 2820.0;
  float ring = 0.5 + 0.5 * cos(TAU * s), pet = 0.5 + 0.5 * cos(5.0 * (th + twist) + 3.0 * lr);
  float v = ring * ring * ring * (0.55 + 0.45 * pet);
  float env = pow(sat((r - 0.04) / 0.25), 2.0) * exp(-(r / 0.75) * (r / 0.75));
  float ph = TAU * (0.4 * lr + t / 1860.0);
  float w1 = 0.5 + 0.5 * cos(ph), w2 = 0.5 + 0.5 * cos(ph + 2.1), w3 = 0.5 + 0.5 * cos(ph + 4.2);
  vec3 col = (hexl(11.0, 15.0, 34.0) * w1 + hexl(7.0, 22.0, 24.0) * w2 + hexl(18.0, 12.0, 34.0) * w3) / (w1 + w2 + w3);
  return hexl(2.0, 3.0, 6.0) + col * v * env * 0.75; }

float ridge(float n) { float r = 1.0 - abs(2.0 * n - 1.0); r = r * r; return r * r * r; }
vec3 bg04(vec2 p, vec2 res, float t) {   // Caustic Floor
  vec2 u = p / res.y; vec2 q = u / 0.11;
  float A = loopf(q + vec2(t / 9000.0, t / 14000.0), t, 2400.0, 2, 0.35), B = loopf(q * 1.07 + vec2(40.0, 13.0) - vec2(t / 12000.0, 0.0), t, 3700.0, 2, 0.35);
  float rA = ridge(A), rB = ridge(B); float net = max(rA, rB) * 0.6 + rA * rB * 2.0;
  float depth = pow(sat(1.15 - u.y), 1.8);
  return lerp3(hexl(3.0, 7.0, 11.0), hexl(1.0, 2.0, 4.0), sat(u.y)) + hexl(12.0, 30.0, 36.0) * min(net, 1.4) * depth * 0.45; }

vec3 bg05(vec2 p, vec2 res, float t) {   // Aurora Veil (green-teal to indigo; the real aurora's red top omitted: red = strain)
  vec2 u = p / res.y; float X = u.x;
  float by = 0.30 + 0.03 * sin(TAU * (X * 0.35 + t / 540.0)) + 0.02 * sin(TAU * (X * 0.9 - t / 840.0) + 1.0);
  float s1 = loopf(vec2(X / 0.22, 3.7), t, 1260.0, 3, 0.4), s2 = loopf(vec2(X / 0.22 + 50.0, 8.1), t, 1980.0, 3, 0.4);
  float st = sat((s1 * 0.7 + s2 * 0.5 - 0.25) * 0.9);
  float d = u.y - by; float prof = d > 0.0 ? exp(-(d / 0.035) * (d / 0.035)) : exp(d / 0.16);
  float cl = fbm(u / 0.3, 2, 0.5); float up = sat(-d / 0.25);
  vec3 col = lerp3(hexl(11.0, 38.0, 32.0), hexl(14.0, 16.0, 40.0), up);
  return hexl(2.0, 3.0, 7.0) * (1.0 - 0.6 * sat(u.y)) + col * prof * st * (0.55 + 0.45 * cl) * 0.9; }

vec3 bg06(vec2 p, vec2 res, float t) {   // Nebula Dust (static)
  vec2 u = p / res.y;
  vec2 w = vec2(fbm(u / 0.5, 2, 0.5), fbm(u / 0.5 + vec2(31.0, 17.0), 2, 0.5)) - 0.5; vec2 q = u + w * 0.35;
  float c = pow(sat((fbm(q / 0.35, 6, 0.55) - 0.38) * 2.4), 1.7);
  float l = fbm(q * 1.1 / 0.18 + vec2(5.0, 9.0), 4, 0.5); float ln = 1.0 - pow(sat(((1.0 - abs(2.0 * l - 1.0)) - 0.55) * 3.0), 2.0) * 0.85;
  vec3 cloud = lerp3(hexl(12.0, 16.0, 34.0), hexl(10.0, 26.0, 30.0), fbm(u / 0.6 + vec2(3.0, 1.0), 2, 0.5));
  return lerp3(hexl(2.0, 3.0, 6.0), hexl(3.0, 4.0, 7.0), sat(u.y)) + cloud * c * ln; }

vec3 bg07(vec2 p, vec2 res, float t) {   // Ink Bloom
  vec2 u = p / res.y;
  float wx = loopf(u / 0.45, t, 5400.0, 2, 0.5) * 0.7 + loopf(u / 0.45 + vec2(9.0, 4.0), t, 7740.0, 2, 0.5) * 0.3;
  float wy = loopf(u / 0.45 + vec2(23.0, 61.0), t, 5400.0, 2, 0.5) * 0.7 + loopf(u / 0.45 + vec2(47.0, 2.0), t, 7740.0, 2, 0.5) * 0.3;
  float n = fbm((u + (vec2(wx, wy) - 0.5) * 0.6) / 0.28, 5, 0.55);
  float body = sat((n - 0.42) * 2.0), e = (n - 0.46) / 0.05, edge = exp(-e * e);
  vec3 ink = lerp3(hexl(10.0, 11.0, 28.0), hexl(11.0, 18.0, 32.0), fbm(u / 0.7 + vec2(7.0, 3.0), 1, 0.5));
  return lerp3(hexl(3.0, 4.0, 9.0), hexl(2.0, 2.0, 5.0), sat(u.y)) + ink * (0.7 * pow(body, 1.5) + 0.3 * edge); }

vec3 bg08(vec2 p, vec2 res, float t) {   // Interference Field (resembles the VPN-lost searchlight; see the guide)
  vec2 u = p / res.y; float a1 = TAU * t / 1500.0, a2 = TAU * t / 2220.0 + 2.0;
  vec2 c1 = vec2(-0.35 + 0.12 * cos(a1), 0.15 + 0.12 * sin(a1)), c2 = vec2(-0.25 + 0.12 * cos(a2), 0.95 + 0.12 * sin(a2));
  float d = length(u - c1) - length(u - c2); float fr = pow(0.5 + 0.5 * cos(TAU * d * 5.0), 3.0);
  float fade = exp(-length(vec2(u.x, u.y - 0.55)) * 0.55);
  return hexl(2.0, 3.0, 6.0) + hexl(11.0, 20.0, 36.0) * fr * fade * 0.9; }

vec3 bg09(vec2 p, vec2 res, float t) {   // Marine Snow: sinking motes in three depth layers
  float px = res.y / 2234.0; vec2 u = p / res.y;
  vec3 c = lerp3(hexl(5.0, 10.0, 16.0), hexl(1.0, 2.0, 3.0), sat(u.y)); float v = 0.0;
  for (int k = 0; k < 3; k++) { float fk = float(k), dep = (fk + 1.0) / 3.0;
    float sp = (0.12 + 0.18 * fk) * 2.0 * px, cell = (110.0 - 25.0 * fk) * px;
    vec2 q = p - vec2(6.0 * px * sin(TAU * t / (240.0 + 90.0 * fk) + fk * 2.0), sp * t);
    vec2 g = floor(q / cell);
    for (int j = -1; j <= 1; j++) { for (int i = -1; i <= 1; i++) {
      vec2 cc = g + vec2(float(i), float(j)); vec4 h = hash42(cc + vec2(fk * 57.0, 11.0));
      if (h.x < 0.55) { vec2 d = q - (cc + 0.15 + 0.7 * h.yz) * cell; float s = max(0.5, (0.5 + 0.9 * dep) * 1.2 * max(px, 0.35));
        v += (0.0035 + 0.006 * pow(dep, 1.5) * h.w) * exp(-dot(d, d) / (2.0 * s * s)); } } } }
  return c + vec3(0.88, 0.94, 1.0) * v * (1.1 - sat(u.y)); }

vec3 bg10(vec2 p, vec2 res, float t) {   // Hadal Glow (static control)
  vec2 u = p / res.y; float asp = res.x / res.y;
  float r = length(vec2((u.x - asp * 0.38) * 0.8, u.y - 1.25)), g = exp(-(r / 0.95) * (r / 0.95));
  float k = length(vec2(u.x - asp * 1.05, u.y + 0.2)) / 0.6, corner = exp(-k * k);
  return hexl(2.0, 3.0, 4.0) + hexl(10.0, 22.0, 33.0) * g + hexl(7.0, 9.0, 26.0) * 0.6 * corner; }

// ---- starfields (owner, 2026-11-01 08:05) ----------------------------------------------------------------
// Comets: deterministic from design time. One 6-minute slot in two holds a comet (mean gap ~12 min), visible
// 70-120 s, crossing 3-6 px/s with a 90-170 px tail. Peak ~sRGB 45 at the head; colourless blue-white.
vec3 comets(vec2 p, vec2 res, float t) {
  float px = res.y / 2234.0, P = 360.0, k0 = floor(t / P); vec3 acc = vec3(0.0);
  for (int k = -1; k <= 0; k++) { float slot = k0 + float(k); vec4 h = hash42(vec2(slot, 911.7));
    if (h.x > 0.5) continue;
    float dur = 70.0 + 50.0 * h.y, t0 = slot * P + h.z * (P - 20.0), a = (t - t0) / dur;
    if (a < 0.0 || a > 1.0) continue;
    vec4 g = hash42(vec2(slot, 37.3)); float ang = 0.35 + 0.5 * g.x + (g.y > 0.5 ? PI : 0.0);   // shallow diagonals
    vec2 dir = vec2(cos(ang), sin(ang)); float spd = (3.0 + 3.0 * g.y) * px;
    vec2 head = vec2(res.x * (0.15 + 0.7 * g.z), res.y * (0.12 + 0.6 * g.w)) + dir * spd * (t - t0 - dur * 0.5);
    float L = (90.0 + 80.0 * h.w) * px; vec2 d = p - head; float al = -dot(d, dir), pe = dot(d, vec2(-dir.y, dir.x));
    float fade = sin(PI * a); fade = fade * fade; float hs = max(0.6, 1.1 * px);
    float hv = exp(-dot(d, d) / (2.0 * hs * hs)), tl = 0.0;
    if (al > 0.0 && al < L) { float w = max(0.6, (0.8 + 2.5 * al / L) * px), fl = 1.0 - al / L; tl = fl * fl * exp(-pe * pe / (2.0 * w * w)); }
    acc += vec3(0.86, 0.92, 1.0) * (0.026 * hv + 0.0045 * tl) * fade; }
  return acc; }

vec3 starSky(vec2 p, vec2 res) { vec2 u = p / res.y;
  vec3 c = lerp3(hexl(2.0, 3.0, 6.0), hexl(5.0, 7.0, 14.0), 0.1 + 0.5 * u.y * u.y);
  return c + hexl(8.0, 11.0, 20.0) * 0.5 * pow(fbm(u * 3.0 + vec2(4.0, 2.0), 4, 0.5), 3.0); }

vec3 bg11(vec2 p, vec2 res, float t) {   // Starfield, still: fixed stars + rare far comets
  float px = res.y / 2234.0;
  float s = starLayer(p, 34.0 * px, 5.0, 0.55, 1.3 * max(px, 0.35), 0.05) + starLayer(p, 15.0 * px, 9.0, 0.35, 0.9 * max(px, 0.35), 0.006);
  return starSky(p, res) + vec3(0.88, 0.93, 1.0) * s; }

// Travelling: five depth shells of stars approach from a vanishing point at (36%, 42%) of the screen. Each shell
// travels far -> near in 6000 s of design time, fading in far and out near, so no star ever pops. At speed 1 a star
// halfway to the edge moves ~0.3-0.7 px/s (measured: the guide).
vec3 bg12(vec2 p, vec2 res, float t) {
  float px = res.y / 2234.0; vec2 q = p - vec2(res.x * 0.36, res.y * 0.42); float v = 0.0;
  for (int i = 0; i < 5; i++) { float fi = float(i), cyc = t / 6000.0 + fi / 5.0, z = 1.0 - fract(cyc), n = floor(cyc);
    float D = 0.35 + 2.65 * z, cell = 150.0 * px; vec2 w = q * D; vec2 g = floor(w / cell);
    float fade = sat((0.97 - z) / 0.25) * sat(z / 0.12); float br = fade * pow(1.0 / D, 0.6);
    for (int j = -1; j <= 1; j++) { for (int k = -1; k <= 1; k++) {
      vec2 c = g + vec2(float(k), float(j)); vec4 h = hash42(c + vec2(fi * 131.0 + n * 17.0, n * 3.0 + 5.0));
      if (h.x < 0.5) { vec2 sp = (c + 0.15 + 0.7 * h.yz) * cell / D; vec2 d = q - sp; float m = pow(1.0 - h.w * 0.999, -1.0 / 2.2);
        float s = max(0.55, 1.2 * max(px, 0.35) * (0.8 + 0.25 / D));
        v += min(0.0016 * pow(m, 1.6), 0.045) * br * exp(-dot(d, d) / (2.0 * s * s)); } } } }
  float bgf = starLayer(p, 22.0 * px, 21.0, 0.3, 0.9 * max(px, 0.35), 0.004);   // the unmoving far field
  return starSky(p, res) + vec3(0.88, 0.93, 1.0) * (v + bgf); }

// ---- output: linear -> sRGB, +-1 LSB triangular dither from a FIXED pattern (a per-frame pattern boils at 3 fps) ----
// mode 0: display; 1: linear, no encode (measurement); 2: sRGB without dither. boost > 0: preview-only gamma (x^0.35).
vec3 encodeOut(vec3 lin, vec2 p, float mode, float boost) {
  if (mode > 0.5 && mode < 1.5) return lin;
  vec3 s = vec3(l2s(lin.x), l2s(lin.y), l2s(lin.z));
  if (boost > 0.5) s = vec3(pow(s.x, 0.35), pow(s.y, 0.35), pow(s.z, 0.35));
  if (mode > 1.5) return s;
  vec4 h = hash42(p + vec2(0.5, 0.5));
  s = s * 255.0 + vec3(h.x + h.y - 1.0, h.z + h.w - 1.0, h.x + h.w - 1.0);
  return vec3(floor(s.x + 0.5), floor(s.y + 0.5), floor(s.z + 0.5)) / 255.0; }

// dispatcher. nc > 0.5: no comets (static renders of b11/b12).
vec3 pick(float id, vec2 p, vec2 res, float t, float nc) {
  int i = int(id + 0.5); vec3 c = vec3(0.0);
  if (i == 1) c = bg01(p, res, t); else if (i == 2) c = bg02(p, res, t); else if (i == 3) c = bg03(p, res, t);
  else if (i == 4) c = bg04(p, res, t); else if (i == 5) c = bg05(p, res, t); else if (i == 6) c = bg06(p, res, t);
  else if (i == 7) c = bg07(p, res, t); else if (i == 8) c = bg08(p, res, t); else if (i == 9) c = bg09(p, res, t);
  else if (i == 10) c = bg10(p, res, t); else if (i == 11) c = bg11(p, res, t); else if (i == 12) c = bg12(p, res, t);
  if ((i == 11 || i == 12) && nc < 0.5) c += comets(p, res, t);
  return c; }
