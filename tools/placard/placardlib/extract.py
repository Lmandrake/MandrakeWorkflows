"""Extraction via Docling, plus the margin-text union pass.

Three measured facts shape this module.

**The preset named for accuracy corrupts tables.** On a 17-page paper,
`table_mode: accurate` fused cells and shifted values upward -- Table 4's
round-1 row came out EMPTY with its numbers in the row above -- while the
faster mode rendered all 8 tables correctly. So the default option profile
here uses the fast table mode. Accuracy is a claim to be measured, not a name
to be trusted.

**OCR on a clean text layer introduces errors.** It corrupted a deck's own
title (an "o" read as "0", another as "e"). So OCR is OFF unless the
text layer is demonstrably thin, and enabling it changes `profile_id`.

**Docling drops the margin and footnote layer.** For example it loses
`arXiv:2310.01798`, `NTR #1`, `NTR #2`, `IJCAI` and `LPSC`, every one of
which the raw text layer retains. Those are citation handles, so a union pass
recovers identifier-shaped tokens only -- not arbitrary text Docling chose to
drop.

Docling is imported LAZILY. `placard.py` must keep running under the system
Python the SessionStart hook falls back to, which has no Docling installed.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys

# Identifier shapes that are institutionally load-bearing: losing one loses a
# citation, a ticket or a repository.
_IDENTIFIER_PATTERNS = (
    r"\bNTR\s*#?\s*\d+\b",
    r"\barXiv:\s*\d{4}\.\d{4,5}(?:v\d+)?\b",
    r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b",
    r"https?://[^\s\)\]\>,;\"']+",
    r"\b(?:IJCAI|LPSC|AAAI|AAMAS|ICLR|NeurIPS|ICML|AGU|IEEE|ACM|SPIE)\b",
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
)
_IDENTIFIER_RE = re.compile("|".join(_IDENTIFIER_PATTERNS))

# Below this many characters per page, the text layer is thin enough that OCR
# is worth its risk. Above it, OCR only introduces errors.
_THIN_TEXT_CHARS_PER_PAGE = 120

DEFAULT_OPTION_PROFILE = "text-v1"

# Spec 3.4: `pages_total` is not a universal denominator. Each format gets the
# unit it actually has, and a format whose unit cannot be counted is reported as
# UNKNOWN rather than zero -- measured in this very module, a spreadsheet came
# out as units_total=0 while holding many tables.
_UNITS_BY_EXT = {
    ".pdf": "page",
    ".pptx": "slide", ".ppt": "slide", ".potx": "slide", ".key": "slide",
    ".docx": "block", ".doc": "block", ".rtf": "block", ".pages": "block",
    ".xlsx": "worksheet", ".xls": "worksheet", ".xlsm": "worksheet",
    ".xltx": "worksheet",
    ".csv": "record", ".tsv": "record",
    ".ipynb": "cell",
    ".png": "asset", ".jpg": "asset", ".jpeg": "asset", ".gif": "asset",
    ".webp": "asset", ".tiff": "asset", ".bmp": "asset", ".svg": "asset",
}
# The margin-union pass reads a PDF text layer, so it applies to PDFs only.
_RAW_LAYER_EXTS = {".pdf"}


def units_kind_for(path) -> str:
    from pathlib import Path as _P
    return _UNITS_BY_EXT.get(_P(str(path)).suffix.lower(), "unit")


class ExtractResult:
    __slots__ = ("pages", "margin", "tables_detected", "tables_exported",
                 "figures_detected", "profile_id", "units_kind", "units_total",
                 "units_known", "units_failed", "ocr_used",
                 "margin_unavailable", "figures")

    def __init__(self, **kw):
        for key in self.__slots__:
            setattr(self, key, kw.get(key))


def docling_available() -> bool:
    try:
        import docling  # noqa: F401
    except Exception:
        return False
    return True


def _soffice_present() -> bool:
    """LibreOffice presence changes what Docling can rasterize (EMF/WMF in Word
    and PowerPoint), so it belongs in the profile identity."""
    if shutil.which("soffice"):
        return True
    try:
        return subprocess.run(
            ["test", "-x", "/Applications/LibreOffice.app/Contents/MacOS/soffice"],
            check=False).returncode == 0
    except Exception:
        return False


def _versions() -> dict:
    out = {}
    try:
        import importlib.metadata as md
        for pkg in ("docling", "docling-core", "docling-ibm-models",
                    "docling-parse"):
            try:
                out[pkg] = md.version(pkg)
            except Exception:
                pass
    except Exception:
        pass
    return out


def profile_id(*, versions: dict, option_profile: str, soffice: bool) -> str:
    """The identity of an extraction. Two extractions sharing an id must be
    interchangeable, so everything that changes the output goes in here."""
    core = versions.get("docling", "unknown")
    extra = versions.get("docling-ibm-models")
    head = f"docling-{core}" + (f"+models-{extra}" if extra else "")
    return f"{head}/{option_profile}/" + ("soffice-present" if soffice
                                          else "soffice-absent")


def current_profile_id(option_profile: str = DEFAULT_OPTION_PROFILE) -> str:
    return profile_id(versions=_versions(), option_profile=option_profile,
                      soffice=_soffice_present())


def margin_identifiers(body_text: str, raw_text: str) -> list:
    """Identifier-shaped tokens present in the raw text layer and absent from
    the structured body. Deliberately narrow: this recovers citation handles,
    not arbitrary text the structured extractor chose to drop."""
    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", s.lower())

    body_flat = norm(body_text)
    found, seen = [], set()
    for match in _IDENTIFIER_RE.finditer(raw_text or ""):
        token = re.sub(r"\s+", " ", match.group(0)).strip().rstrip(".,;:")
        key = norm(token)
        if not key or key in seen or key in body_flat:
            continue
        seen.add(key)
        found.append(token)
    return found


def _raw_text_layer(path) -> tuple:
    """(raw text, unavailable_reason).

    Returns the reason rather than swallowing it. An earlier version returned
    "" on any failure, which made the whole margin-union pass INERT whenever
    pypdf was missing from the interpreter -- present in the code, reported as
    working, recovering nothing. A feature that silently does nothing is worse
    than one that is absent, so the reason travels with the result and
    `extract()` records it.
    """
    try:
        import pypdf
    except ImportError:
        return "", ("pypdf is not installed in this interpreter, so margin and "
                    "footnote identifiers could not be recovered. "
                    "Fix: uv pip install --python .venv/bin/python pypdf")
    try:
        reader = pypdf.PdfReader(str(path))
        return "\n".join((p.extract_text() or "") for p in reader.pages), None
    except Exception as exc:
        return "", f"raw text layer unreadable ({type(exc).__name__}: {exc})"


def figure_records(doc) -> list:
    """(page, png_bytes, caption, docling_class, area_frac) per picture.

    Everything is read defensively: Docling's picture API has moved between
    versions, and a figure whose bytes cannot be obtained must be reported as
    undescribable rather than silently dropped from the denominator.
    """
    out = []
    for pic in list(getattr(doc, "pictures", []) or []):
        page, area = 1, None
        prov = getattr(pic, "prov", None)
        if prov:
            page = getattr(prov[0], "page_no", 1) or 1
            bbox = getattr(prov[0], "bbox", None)
            if bbox is not None:
                try:
                    area = abs((bbox.r - bbox.l) * (bbox.t - bbox.b))
                except Exception:
                    area = None

        caption = None
        for attr in ("caption_text",):
            fn = getattr(pic, attr, None)
            if callable(fn):
                try:
                    caption = fn(doc) or None
                except Exception:
                    caption = None
            if caption:
                break

        cls = None
        for ann in list(getattr(pic, "annotations", []) or []):
            predicted = getattr(ann, "predicted_classes", None)
            if predicted:
                cls = getattr(predicted[0], "class_name", None)
                break

        data = None
        getter = getattr(pic, "get_image", None)
        if callable(getter):
            try:
                import io
                image = getter(doc)
                if image is not None:
                    buf = io.BytesIO()
                    image.save(buf, format="PNG")
                    data = buf.getvalue()
            except Exception:
                data = None
        out.append((page, data, caption, cls, area))
    return out


def _convert(path, *, do_ocr: bool, want_figures: bool = False):
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions, TableFormerMode)
    from docling.document_converter import DocumentConverter, PdfFormatOption

    opts = PdfPipelineOptions()
    opts.do_ocr = do_ocr
    opts.do_table_structure = True
    # Measured: the ACCURATE mode fused cells and shifted values upward on a
    # real paper; FAST rendered all 8 tables correctly.
    opts.table_structure_options.mode = TableFormerMode.FAST
    # Picture images and classification cost time, so they are only turned on
    # when a description pass will actually use them.
    opts.do_picture_classification = want_figures
    opts.do_picture_description = False      # Placard describes, not Docling
    opts.generate_picture_images = want_figures
    if want_figures:
        opts.images_scale = 2.0

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    return converter.convert(str(path)).document


def _page_buckets(doc, stats=None) -> dict:
    """Per-page text, in page order, using Docling's provenance.

    A table item has no `.text` attribute -- its content lives in `.data`,
    reachable only through `export_to_markdown()` -- so a page whose entire
    content is tabular fell straight through the `if not text` guard below
    and left that page's bucket empty. For a spreadsheet, EVERY page is a
    worksheet rendered as one table, so this produced `pages=[]` -- an empty
    `## Full text` section -- on a file Docling had parsed correctly and
    whose `tables_detected` was already nonzero. Measured on 16
    real xlsx digests. A table is now rendered to markdown and bucketed by page
    like any other item.
    """
    buckets: dict = {}
    for item, _level in doc.iterate_items():
        text = getattr(item, "text", None)
        if not text or not text.strip():
            export = getattr(item, "export_to_markdown", None)
            if callable(export):
                try:
                    text = export(doc)
                except Exception:
                    text = None
                    if stats is not None:
                        stats["export_failed"] = stats.get("export_failed", 0) + 1
        if not text or not text.strip():
            continue
        text = _DATA_URI_IMAGE.sub(_image_placeholder, text)
        page = 1
        prov = getattr(item, "prov", None)
        if prov:
            page = getattr(prov[0], "page_no", 1) or 1
        buckets.setdefault(page, []).append(text.strip())
    return buckets


def _pages_from(doc, stats=None) -> list:
    buckets = _page_buckets(doc, stats)
    return ["\n".join(buckets[p]) for p in sorted(buckets)]


# A picture item's markdown export inlines the image as a base64 data URI. On
# the shipped example deck that was 30 KB of a 34 KB body: the body is text, and
# the picture is accounted for by the figure pass, so the pixels are replaced
# by a marker rather than carried as unreadable bytes.
_DATA_URI_IMAGE = re.compile(r"!\[([^\]]*)\]\(data:[^)]*\)")


def _image_placeholder(match) -> str:
    alt = match.group(1).strip()
    return f"[picture: {alt}]" if alt and alt.lower() != "image" else "[picture]"


def pptx_speaker_notes(path) -> dict:
    """{slide_number: notes text} read straight from the package, stdlib only.

    Docling drops speaker notes, and in a deck the notes are often where the
    numbers and the reasoning live (on the shipped example: the supplier, the
    unit price, and the consequence of deferring). Slide order comes from
    presentation.xml, not file names, because slides are renumbered on reorder.
    """
    import posixpath
    import zipfile
    from xml.etree import ElementTree as ET

    ns_p = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
    ns_r = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    ns_rel = "{http://schemas.openxmlformats.org/package/2006/relationships}"
    ns_a = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

    def rels(z, part):
        d, b = posixpath.split(part)
        name = posixpath.join(d, "_rels", b + ".rels")
        if name not in z.namelist():
            return {}
        out = {}
        for rel in ET.fromstring(z.read(name)).iter(ns_rel + "Relationship"):
            target = posixpath.normpath(posixpath.join(d, rel.get("Target", "")))
            out[rel.get("Id")] = (rel.get("Type", ""), target)
        return out

    notes = {}
    with zipfile.ZipFile(path) as z:
        pres = "ppt/presentation.xml"
        pres_rels = rels(z, pres)
        ids = ET.fromstring(z.read(pres)).find(ns_p + "sldIdLst")
        order = [pres_rels[e.get(ns_r + "id")][1] for e in (ids if ids is not None else [])
                 if e.get(ns_r + "id") in pres_rels]
        for number, slide in enumerate(order, 1):
            for kind, target in rels(z, slide).values():
                if not kind.endswith("/notesSlide") or target not in z.namelist():
                    continue
                root = ET.fromstring(z.read(target))
                paras = []
                for sp in root.iter(ns_p + "sp"):
                    ph = sp.find(f"{ns_p}nvSpPr/{ns_p}nvPr/{ns_p}ph")
                    if ph is None or ph.get("type") != "body":
                        continue          # skip the slide image and number
                    for para in sp.iter(ns_a + "p"):
                        line = "".join(t.text or "" for t in para.iter(ns_a + "t")).strip()
                        if line:
                            paras.append(line)
                if paras:
                    notes[number] = "\n".join(paras)
    return notes


def extract(path, *, option_profile: str = DEFAULT_OPTION_PROFILE,
            want_figures: bool = False) -> ExtractResult:
    """Extract one artifact. Raises RuntimeError if Docling is unavailable --
    never returns an error string as content, which is how v1 produced bodies
    flagged `full` whose entire content was an exception message.
    """
    if not docling_available():
        raise RuntimeError(
            "docling is not importable in this interpreter. Run extraction with "
            "Placard's venv: .venv/bin/python placard.py digest <artifact>")

    doc = _convert(path, do_ocr=False, want_figures=want_figures)
    pages = _pages_from(doc)
    chars = sum(len(p) for p in pages)
    ocr_used = False
    # Evidence, not a preset: OCR only where the text layer is demonstrably thin.
    if pages and chars / max(1, len(pages)) < _THIN_TEXT_CHARS_PER_PAGE:
        doc = _convert(path, do_ocr=True, want_figures=want_figures)
        pages = _pages_from(doc)
        ocr_used = True
    elif not pages:
        doc = _convert(path, do_ocr=True, want_figures=want_figures)
        pages = _pages_from(doc)
        ocr_used = True

    tables = list(getattr(doc, "tables", []) or [])
    pictures = list(getattr(doc, "pictures", []) or [])

    from pathlib import Path as _P
    suffix = _P(str(path)).suffix.lower()
    stats: dict = {}
    if suffix == ".pptx":
        buckets = _page_buckets(doc, stats)
        try:
            notes = pptx_speaker_notes(path)
        except Exception as exc:   # a damaged package still has its slide text
            notes = {}
            print(f"warning: speaker notes unreadable ({type(exc).__name__})",
                  file=sys.stderr)
        for number, text in notes.items():
            buckets.setdefault(number, []).append("Speaker notes: " + text)
        pages = ["\n".join(buckets[p]) for p in sorted(buckets)]
    else:
        pages = _pages_from(doc, stats)
    body = "\n".join(pages)
    if suffix in _RAW_LAYER_EXTS:
        raw, margin_unavailable = _raw_text_layer(path)
    else:
        raw, margin_unavailable = "", None   # not applicable, not a failure
    margin = margin_identifiers(body, raw)

    # Honest denominator. Text buckets give the unit count only where the unit
    # IS a text-bearing page/slide. A spreadsheet's content is its tables, so
    # counting text buckets there reported 0 while many tables sat in the file.
    # The denominator comes from the document, not from the text that survived:
    # counting text buckets let a page that yielded nothing vanish from both
    # sides of the fraction instead of showing up as failed.
    units_kind = units_kind_for(path)
    doc_pages = getattr(doc, "pages", None)
    if isinstance(doc_pages, dict) and doc_pages:
        units_total, units_known = len(doc_pages), True
        units_failed = max(0, units_total - len(pages))
    else:
        units_total, units_known, units_failed = len(pages), bool(pages), 0
        if not pages and (tables or pictures):
            units_known = False   # content exists; the unit count does not
    tables_failed = stats.get("export_failed", 0)

    effective_profile = option_profile + ("+ocr" if ocr_used else "")
    return ExtractResult(
        pages=pages,
        margin=margin,
        tables_detected=len(tables),
        tables_exported=max(0, len(tables) - tables_failed),
        figures_detected=len(pictures),
        profile_id=profile_id(versions=_versions(),
                             option_profile=effective_profile,
                             soffice=_soffice_present()),
        units_kind=units_kind,
        units_total=units_total,
        units_known=units_known,
        units_failed=units_failed,
        ocr_used=ocr_used,
        margin_unavailable=margin_unavailable,
        figures=figure_records(doc) if want_figures else [],
    )
