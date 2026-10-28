"""Figures: three distinct records, gated effort, honest accounting.

A figure review over 31 real figures established that the value of a vision
description is CONCENTRATED: four figures carried half the novel vocabulary,
ten added one term or none for ~2,000 characters each, and seven were
institutional furniture. So effort is gated -- but every exclusion is counted
with its reason, because "skipped as logo", "classification uncertain" and
"description failed" must never collapse into "figures complete".

Three records, deliberately separate:

  * **Observation** -- reusable facts about the rendered pixels, keyed by
    content hash.
  * **Occurrence** -- where the image appears: page, caption, role.
  * **Description** -- generated text, always labelled generated and never
    presented as the document's own caption.

Dedup reuses the OBSERVATION and never collapses occurrences. The same bitmap
can appear once as "input" and once as "reconstruction"; one description, two
occurrences, two roles. Perceptual similarity is deliberately NOT used -- it
would collapse two near-identical charts differing in the one curve that
matters.
"""
from __future__ import annotations

import hashlib
import os
import re
from collections import Counter

# 🔴 Docling emits class names in snake_case -- measured against docling
# 2.115.0 on a real deck: logo, icon, full_page_image, photograph, flow_chart,
# line_chart, engineering_drawing, screenshot_from_computer, other.
#
# The first version of this gate compared against Title Case strings ("Logo",
# "Flow chart"). Every comparison missed, so every figure fell through to the
# default depth and the gate was INERT against real data -- while its unit
# tests passed, because those fixtures used the same assumed vocabulary the
# code did. A test that encodes the wrong vocabulary cannot catch the wrong
# vocabulary. So names are normalized before comparison and the measured
# vocabulary is pinned by a test.
def normalize_class(name) -> str:
    if not name:
        return ""
    return "_".join(str(name).strip().lower().replace("-", " ").split())


# Classes that are institutional furniture on a page.
FURNITURE_CLASSES = {
    "logo", "icon", "full_page_image", "signature", "stamp",
}
# Classes whose meaning is their structure, which no caption and no text layer
# carries.
STRUCTURAL_CLASSES = {
    "flow_chart", "engineering_drawing", "line_chart", "bar_chart",
    "pie_chart", "scatter_plot", "screenshot_from_computer", "map",
    "chemistry_markush_structure", "chemistry_molecular_structure",
    "signature_or_stamp", "sketch", "geographic_map",
}

# Below this fraction of the page, an unclassified image is decoration.
_TINY_AREA_FRAC = 0.002
# A caption needs some substance before it can stand in for a description.
_INFORMATIVE_CAPTION_WORDS = 8

# A directory needs at least this many images, and this share of them sharing a
# stem, before it is a generated collection rather than a set of real figures.
_COLLECTION_MIN_IMAGES = 20
_COLLECTION_SHARE = 0.6


class Decision:
    __slots__ = ("depth", "reason")

    def __init__(self, depth: str, reason: str):
        self.depth = depth
        self.reason = reason

    def __repr__(self) -> str:
        return f"Decision({self.depth!r}, {self.reason!r})"


def _caption_is_informative(caption) -> bool:
    if not caption:
        return False
    stripped = re.sub(r"^\s*(?:figure|fig\.?|table|plate)\s*\d+[.:]?\s*", "",
                      caption, flags=re.IGNORECASE)
    return len(stripped.split()) >= _INFORMATIVE_CAPTION_WORDS


def decide(*, docling_class, area_frac, caption) -> Decision:
    """How much effort this figure earns, and why."""
    key = normalize_class(docling_class)

    if key in FURNITURE_CLASSES:
        return Decision("skip", f"{key} — institutional furniture, "
                                f"describing it is spend rather than capture")

    if key in STRUCTURAL_CLASSES:
        # A caption cannot close a structural gap: "Performance across
        # datasets" does not tell you the axes, the units or the trend.
        return Decision("full", f"{key} — structure and axes are "
                                f"content no caption or text layer carries")

    if not key:
        if area_frac is not None and area_frac < _TINY_AREA_FRAC:
            return Decision("skip", "unclassified and below the decoration "
                                    "area threshold")
        return Decision("brief", "unclassified by the detector — described "
                                 "briefly rather than skipped silently")

    if _caption_is_informative(caption):
        return Decision("caption-only", "the document's own caption already "
                                        "names the content")
    return Decision("brief", f"{key} — a line names what is in it")


class Observation:
    __slots__ = ("key", "nbytes", "description", "depth", "skip_reason")

    def __init__(self, key: str, nbytes: int):
        self.key = key
        self.nbytes = nbytes
        self.description = None
        self.depth = None
        self.skip_reason = None


class Occurrence:
    __slots__ = ("page", "observation_key", "caption", "role", "docling_class",
                 "decision")

    def __init__(self, page, observation_key, caption, role, docling_class,
                 decision):
        self.page = page
        self.observation_key = observation_key
        self.caption = caption
        self.role = role
        self.docling_class = docling_class
        self.decision = decision


class Inventory:
    """Observations deduplicated by content hash; occurrences never merged."""

    def __init__(self):
        self.observations: dict = {}
        self.occurrences: list = []

    def add(self, *, page, image_bytes, caption=None, role=None,
            docling_class=None, area_frac=None) -> Occurrence:
        key = hashlib.sha256(image_bytes).hexdigest()
        obs = self.observations.get(key)
        if obs is None:
            obs = Observation(key, len(image_bytes))
            self.observations[key] = obs
        decision = decide(docling_class=docling_class, area_frac=area_frac,
                          caption=caption)
        # The observation records the DEEPEST effort any occurrence justifies:
        # a bitmap reused as decoration on one page and as a figure on another
        # must still be described.
        order = {"skip": 0, "caption-only": 1, "brief": 2, "full": 3}
        if obs.depth is None or order[decision.depth] > order[obs.depth]:
            obs.depth = decision.depth
            obs.skip_reason = (decision.reason if decision.depth == "skip"
                               else None)
        occ = Occurrence(page, key, caption, role, docling_class, decision)
        self.occurrences.append(occ)
        return occ

    def accounting(self) -> dict:
        skipped = [o for o in self.occurrences if o.decision.depth == "skip"]
        described = [o for o in self.occurrences if o.decision.depth != "skip"]
        reasons = Counter(
            (o.docling_class or "unclassified") for o in skipped)
        return {
            "figures_detected": len(self.occurrences),
            "figures_detected_known": "true",
            "unique_images": len(self.observations),
            "captions_associated": sum(1 for o in self.occurrences if o.caption),
            "descriptions_planned": len(described),
            "descriptions_skipped": len(skipped),
            "skip_reasons": dict(reasons),
        }


def accounting_unknown(note: str) -> dict:
    """Detection failed or was unavailable. An unknown total must never be
    rendered as zero: absence of data is not absence of figures."""
    return {
        "figures_detected_known": "false",
        "figures_detection_note": note,
    }


class DirectoryVerdict:
    __slots__ = ("is_collection", "count", "shared_stem", "shared_tokens",
                 "reason")

    def __init__(self, is_collection, count, shared_tokens, reason):
        self.is_collection = is_collection
        self.count = count
        self.shared_tokens = shared_tokens
        self.shared_stem = "_".join(shared_tokens)
        self.reason = reason


_EXT_TOKENS = {"png", "jpg", "jpeg", "gif", "svg", "webp", "tif", "tiff", "bmp"}


def _content_tokens(name: str) -> set:
    """Word-ish tokens in a filename, minus the extension.

    A shared PREFIX was the first thing tried and it failed on the real corpus:
    `RUN_A_XY_convergence.png` beside `RUN_B_XY_convergence.png` share
    no stem but are plainly one family. Shared tokens find them.
    """
    base = os.path.splitext(name)[0].lower()
    return {t for t in re.findall(r"[a-z]{3,}", base) if t not in _EXT_TOKENS}


def classify_directory(image_names: list) -> DirectoryVerdict:
    """Is this a directory of homogeneous generated output?

    Generated analysis plots often sit in one tree, with hundreds of
    near-identical files in a single directory. Describing
    those individually buys nothing; the FAMILY needs one digest naming its
    generator and axes of variation.

    Calibrated against the real directories, which separate cleanly:
      dir_a (90)                  'tokena' 100%, 'tokenb' 100%   -> collection
      dir_b (160)              'tokenc' 84%              -> collection
      dir_c (121)                    'tokend' 61%                  -> collection
      dir_d (93)           best token 4%               -> real figures
      dir_e (21)                   best token 5%               -> real figures
    """
    names = [n for n in image_names if n]
    if len(names) < _COLLECTION_MIN_IMAGES:
        return DirectoryVerdict(False, len(names), [],
                                f"only {len(names)} images; below the "
                                f"collection threshold of "
                                f"{_COLLECTION_MIN_IMAGES}")
    counts: Counter = Counter()
    for name in names:
        for token in _content_tokens(name):
            counts[token] += 1
    if not counts:
        return DirectoryVerdict(False, len(names), [],
                                "filenames carry no word-like tokens to compare")

    need = _COLLECTION_SHARE * len(names)
    shared = [t for t, c in counts.most_common() if c >= need]
    top, hits = counts.most_common(1)[0]
    if not shared:
        return DirectoryVerdict(
            False, len(names), [],
            f"no token is shared widely enough (best: {top!r} in "
            f"{100 * hits / len(names):.0f}% of {len(names)} names) — these "
            f"look like distinct figures")

    # Order the shared tokens as they appear in a representative name, so the
    # family reads like a name rather than a frequency list.
    probe = sorted(names)[len(names) // 2]
    order = [t for t in re.findall(r"[a-z]{3,}", os.path.splitext(probe)[0].lower())
             if t in set(shared)]
    ordered = list(dict.fromkeys(order)) or shared
    return DirectoryVerdict(
        True, len(names), ordered,
        f"{hits} of {len(names)} names share {top!r} — generated output; "
        f"one collection digest instead of {len(names)} descriptions")
