#!/usr/bin/env python3
"""Build the synthetic example folder: a PDF report, a slide deck and a spreadsheet.

Everything here is invented: the cooperative, the sites, the supplier and every number. The
facts are written once, in FACTS, and each artifact draws from them, so the question set in
`questions.json` has a known answer that does not depend on any model.

    python3 examples/make_example.py          # needs python-pptx, openpyxl, Pillow

The PDF is written by a small stdlib writer (Helvetica, no dependency). The built files are
committed, so nothing else in the repo needs these libraries; this script is their provenance.
"""
from __future__ import annotations

import io
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent / "quarterly-review"

SITES = [  # name, units, baseline m3 (2025 season), trial m3 (2026)
    ("Alder Flat", 12, 4820, 3610),
    ("Birch Hollow", 12, 5140, 4010),
    ("Cedar Ridge", 12, 4460, 3700),
    ("Dunmore", 12, 5580, 4060),
]
WEEKS = 12


def pct(base, trial):
    return round(100.0 * (base - trial) / base, 1)


TOTAL_BASE = sum(s[2] for s in SITES)
TOTAL_TRIAL = sum(s[3] for s in SITES)
TOTAL_PCT = pct(TOTAL_BASE, TOTAL_TRIAL)


# --------------------------------------------------------------------------- weekly log
def weekly_rows():
    """48 rows whose per-site water sums equal the trial totals exactly."""
    shape = [1.10, 1.14, 1.16, 1.12, 1.06, 1.00, 0.98, 0.94, 0.90, 0.88, 0.86, 0.86]
    rows = []
    for si, (name, _u, _b, trial) in enumerate(SITES):
        raw = [trial * w / sum(shape) for w in shape]
        vals = [int(round(v)) for v in raw]
        vals[-1] += trial - sum(vals)
        for wk in range(WEEKS):
            moisture = round(24.0 + 1.5 * si + 0.35 * wk - (0.8 if wk % 3 == 0 else 0), 1)
            alerts = (si * 3 + wk * 5) % 4
            if name == "Cedar Ridge" and wk + 1 == 7:
                alerts = 9  # the stiction cluster: the single worst week
            rows.append((wk + 1, name, vals[wk], moisture, alerts))
    return rows


# --------------------------------------------------------------------------- PDF writer
def _esc(s):
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf(path, pages):
    """pages: list of lists of (x, y, size, text) or ('rule', x1, y, x2)."""
    objs = []

    def add(b):
        objs.append(b)
        return len(objs)

    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    bold = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    page_ids, pages_id = [], len(objs) + 1 + 2 * len(pages)
    for items in pages:
        ops = []
        for it in items:
            if it[0] == "rule":
                _, x1, y, x2 = it
                ops.append(f"0.5 w {x1} {y} m {x2} {y} l S")
            else:
                x, y, size, text, *style = it
                f = "F2" if style and style[0] == "b" else "F1"
                ops.append(f"BT /{f} {size} Tf {x} {y} Td ({_esc(text)}) Tj ET")
        data = zlib.compress("\n".join(ops).encode("latin-1"))
        content = add(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(data)
                      + data + b"\nendstream")
        page_ids.append(add(
            b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 612 792] /Contents %d 0 R "
            b"/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> >>"
            % (pages_id, content, font, bold)))
    kids = " ".join(f"{p} 0 R" for p in page_ids).encode()
    assert add(b"<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(page_ids))) == pages_id
    info = add(b"<< /Title (DC-7 Drip Controller Field Trial) /Producer (make_example.py) >>")
    catalog = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id)
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % i + body + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
    for off in offsets:
        out.write(b"%010d 00000 n \n" % off)
    out.write(b"trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
              % (len(objs) + 1, catalog, info, xref))
    Path(path).write_bytes(out.getvalue())


def wrap(text, width=92):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    return lines + ([cur] if cur else [])


def report_pages():
    paras = {
        1: ("Summary", [
            "Northwind Irrigation Cooperative ran a twelve-week field trial of the DC-7 drip "
            "controller from 6 July to 27 September 2026, on four member sites with twelve "
            "controllers each (48 units in all).",
            f"Across the four sites the trial plots used {TOTAL_TRIAL:,} cubic metres of water "
            f"against a 2025 baseline of {TOTAL_BASE:,}, a reduction of {TOTAL_PCT}%. Every "
            "site improved; the smallest gain was at Cedar Ridge.",
            "Two problems were found: valve stiction at Cedar Ridge and clock drift in "
            "firmware 2.3.1. Both have a fix, described in Section 4.",
        ]),
        2: ("2. Method", [
            "The baseline is the same plots in the 2025 season, irrigated on fixed timers. "
            "Flow meters were read weekly by site stewards; soil moisture was logged at 30 cm "
            "by one capacitive probe per plot.",
            "Weeks are numbered 1 to 12 from the week of 6 July. Weekly readings, soil "
            "moisture and controller alerts are in the companion spreadsheet, "
            "sensor-log.xlsx, sheet weekly_readings.",
            "Rainfall during the trial was within 8% of the 2025 season at every site, so "
            "no weather correction was applied.",
        ]),
        4: ("4. Problems found", [
            "Valve stiction. At Cedar Ridge, 5 of the 12 controllers reported a valve that "
            "failed to close fully, mostly in week 7. The cause was scale from hard well "
            "water. An inline filter cures it; a retrofit is planned for every unit before "
            "any expansion.",
            "Clock drift. Firmware 2.3.1 lost up to 9 minutes a week, which shifted watering "
            "windows into the afternoon. Firmware 2.3.4, installed on 18 August, fixed it; no "
            "drift was seen after that date.",
        ]),
        5: ("5. Recommendation", [
            "Expand to 200 controllers for the 2027 season, conditional on the filter "
            "retrofit. The operations board decides at its meeting on 12 November 2026.",
            "Contact for this report: the cooperative's operations team.",
        ]),
    }
    pages = []
    for n in range(1, 6):
        items = [(72, 750, 9, "Northwind Irrigation Cooperative  |  DC-7 Field Trial Report"),
                 ("rule", 72, 742, 540), (300, 40, 9, f"{n}")]
        y = 700
        if n == 1:
            items.append((72, y, 18, "DC-7 Drip Controller Field Trial, Q3 2026", "b"))
            y -= 40
        if n == 3:
            items.append((72, y, 13, "3. Results by site", "b"))
            y -= 28
            items.append((72, y, 10, "Table 1. Water use by site, cubic metres.", "b"))
            y -= 22
            cols = [72, 200, 260, 360, 460]
            for x, h in zip(cols, ["Site", "Units", "Baseline 2025", "Trial 2026", "Reduction %"]):
                items.append((x, y, 10, h, "b"))
            items.append(("rule", 72, y - 6, 540))
            y -= 22
            for name, units, base, trial in SITES:
                for x, v in zip(cols, [name, str(units), f"{base:,}", f"{trial:,}",
                                       f"{pct(base, trial)}"]):
                    items.append((x, y, 10, v))
                y -= 18
            items.append(("rule", 72, y + 10, 540))
            for x, v in zip(cols, ["Total", "48", f"{TOTAL_BASE:,}", f"{TOTAL_TRIAL:,}",
                                   f"{TOTAL_PCT}"]):
                items.append((x, y - 6, 10, v, "b"))
            y -= 50
            best = max(SITES, key=lambda s: pct(s[2], s[3]))
            for line in wrap(f"{best[0]} gained most ({pct(best[2], best[3])}%). Cedar Ridge "
                             "gained least, and its result is depressed by the valve fault "
                             "in Section 4."):
                items.append((72, y, 11, line))
                y -= 15
        else:
            title, body = paras[n]
            items.append((72, y, 13, title, "b"))
            y -= 26
            for para in body:
                for line in wrap(para):
                    items.append((72, y, 11, line))
                    y -= 15
                y -= 10
        pages.append(items)
    return pages


# --------------------------------------------------------------------------- chart PNG
def chart_png():
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1200, 700
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.load_default(size=30)
        small = ImageFont.load_default(size=24)
    except TypeError:
        font = small = ImageFont.load_default()
    d.text((60, 20), "Water saved by site, % vs 2025", fill="black", font=font)
    x0, y0, y1 = 120, 620, 120
    scale = (y0 - y1) / 30.0
    d.line([(x0, y0), (x0, y1)], fill="black", width=3)
    d.line([(x0, y0), (W - 60, y0)], fill="black", width=3)
    for tick in (0, 10, 20, 30):
        y = y0 - tick * scale
        d.text((50, y - 14), f"{tick}%", fill="black", font=small)
    for i, (name, _u, base, trial) in enumerate(SITES):
        v = pct(base, trial)
        bx = x0 + 60 + i * 250
        d.rectangle([bx, y0 - v * scale, bx + 150, y0], fill=(70, 120, 180))
        d.text((bx, y0 + 12), name, fill="black", font=small)
    ty = y0 - 20 * scale
    for x in range(x0, W - 60, 24):
        d.line([(x, ty), (x + 12, ty)], fill=(200, 40, 40), width=4)
    d.text((W - 330, ty - 40), "board target 20%", fill=(200, 40, 40), font=small)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


# --------------------------------------------------------------------------- deck
def write_deck(path):
    from pptx import Presentation
    from pptx.util import Inches, Pt
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    def slide(title, bullets, notes, image=None):
        s = prs.slides.add_slide(prs.slide_layouts[5])
        s.shapes.title.text = title
        if bullets:
            box = s.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(11.5), Inches(5))
            tf = box.text_frame
            tf.word_wrap = True
            for i, b in enumerate(bullets):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                p.text = b
                p.font.size = Pt(24)
        if image:
            s.shapes.add_picture(io.BytesIO(image), Inches(2.2), Inches(1.5), height=Inches(5.6))
        s.notes_slide.notes_text_frame.text = notes

    slide("DC-7 Field Trial: Q3 Review", ["Northwind Irrigation Cooperative",
                                          "Operations team, October 2026"],
          "Ten minutes, then questions.")
    slide(f"{TOTAL_PCT}% less water", [
        "48 controllers, 4 sites, 12 weeks", "Every site beat its 2025 baseline"],
        "Dunmore did best because its plots are on sandy soil, where fixed timers "
        "over-watered the most.")
    slide("Results by site", [], "The dashed line is the target the board set in the spring.",
          image=chart_png())
    slide("What went wrong", [
        "Valve stiction at Cedar Ridge: 5 of 12 units, hard-water scale",
        "Clock drift in firmware 2.3.1, fixed by 2.3.4"],
        "The filter retrofit is quoted by Tallis Supply at $38 per unit, three weeks lead time.")
    slide("The 2027 ask", [
        "200 controllers at $260: $52,000", "Inline filters at $38: $7,600",
        "Installation: $1,800", "Total: $61,400"],
        "Installation is low because site stewards do it; the $1,800 is tools and travel.")
    slide("Timeline", [
        "Board vote: 12 November 2026", "Procurement: January 2027",
        "Install: March 2027, before planting"],
        "If the board defers, the earliest install slips to the 2028 season because of the "
        "planting calendar.")
    slide("Questions", [], "Spreadsheet and report are in the same folder.")
    prs.save(path)


# --------------------------------------------------------------------------- spreadsheet
def write_xlsx(path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "weekly_readings"
    ws.append(["week", "site", "water_m3", "soil_moisture_pct", "alerts"])
    for row in weekly_rows():
        ws.append(list(row))
    b = wb.create_sheet("budget_2027")
    b.append(["item", "quantity", "unit_cost_usd", "total_usd"])
    for item, q, c in [("DC-7 controller", 200, 260), ("Inline filter", 200, 38),
                       ("Installation (tools, travel)", 1, 1800)]:
        b.append([item, q, c, q * c])
    b.append(["Total", None, None, 52000 + 7600 + 1800])
    wb.properties.creator = "make_example.py"
    wb.save(path)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    write_pdf(OUT / "field-trial-report.pdf", report_pages())
    write_deck(OUT / "review-deck.pptx")
    write_xlsx(OUT / "sensor-log.xlsx")
    for p in sorted(OUT.iterdir()):
        if p.suffix in (".pdf", ".pptx", ".xlsx"):
            print(f"{p.name}: {p.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
