#!/usr/bin/env python3
"""Run an executor's chart script with Figure.savefig instrumented; dump what each saved figure holds.

  python instrument.py <script.py> <dump.json>      (cwd = a copy of the final workspace)

At every savefig, after the real save (so ticks and layout are drawn), it records the figure's
axes (limits, scales, facecolor, colorbar flag), bars (BarContainer patches), other rectangles and
circles, lines (data-space xy via get_xydata, so dates and categories are already converted),
collections (offsets, sizes, facecolors, colour array, colormap), images (colormap, shape, clim),
and every visible text with its colour, alpha, size and the background it sits on (axes facecolor
for in-axes text, its bbox facecolor if it has one, else the saved figure facecolor). Colormaps are
recorded by name AND by 64 RGB samples, so a renamed copy of jet is still recognisable.
"""
import json, os, runpy, sys, traceback
import matplotlib
matplotlib.use("Agg")
import numpy as np
from matplotlib import colors as mcolors
from matplotlib.collections import Collection, PathCollection, LineCollection
from matplotlib.container import BarContainer
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Ellipse, Rectangle
from matplotlib.text import Text

DUMPS = []
_ORIG = Figure.savefig
CAP = 3000


def rgba(c):
    try:
        return [round(float(x), 4) for x in mcolors.to_rgba(c)]
    except Exception:
        return None


def flist(a, cap=CAP):
    try:
        a = np.asarray(a, dtype=float).ravel()
    except Exception:
        return None
    return [None if not np.isfinite(x) else round(float(x), 6) for x in a[:cap]]


def cmap_info(cm):
    if cm is None:
        return None
    try:
        return {"name": cm.name, "samples": [[round(float(v), 4) for v in cm(i / 63.0)[:3]] for i in range(64)]}
    except Exception:
        return {"name": getattr(cm, "name", None), "samples": None}


def solid_bg(c, fallback):
    c = rgba(c)
    if c is None or c[3] < 0.05:
        return fallback
    if c[3] < 1:  # blend over fallback
        return [round(c[i] * c[3] + fallback[i] * (1 - c[3]), 4) for i in range(3)] + [1.0]
    return c


def text_rec(t, kind, bg):
    try:
        s = t.get_text()
    except Exception:
        return None
    if not isinstance(s, str) or not s.strip() or not t.get_visible():
        return None
    bb = t.get_bbox_patch()
    if bb is not None and bb.get_visible():
        bg = solid_bg(bb.get_facecolor(), bg)
    a = t.get_alpha()
    return {"kind": kind, "text": s, "color": rgba(t.get_color()), "alpha": 1.0 if a is None else float(a),
            "size": float(t.get_fontsize()), "weight": str(t.get_fontweight()), "bg": bg}


def visible_ticklabels(axis):
    out = []
    try:
        ticks = axis._update_ticks()
    except Exception:
        ticks = []
    for tk in ticks:
        for lab in (tk.label1, tk.label2):
            if lab.get_visible():
                out.append(lab)
    return out


def axes_rec(ax, fig_bg):
    is_cb = hasattr(ax, "_colorbar") or ax.get_label() == "<colorbar>"
    ax_bg = solid_bg(ax.get_facecolor(), fig_bg) if ax.patch.get_visible() else fig_bg
    a = {"is_colorbar": is_cb, "visible": ax.get_visible(), "xlim": flist(ax.get_xlim()), "ylim": flist(ax.get_ylim()),
         "xscale": ax.get_xscale(), "yscale": ax.get_yscale(), "facecolor": ax_bg, "bars": [], "rects": [],
         "circles": [], "lines": [], "collections": [], "images": [], "texts": []}
    bar_ids = set()
    for c in ax.containers:
        if isinstance(c, BarContainer):
            ps = [p for p in c.patches if p.get_visible()]
            bar_ids |= {id(p) for p in c.patches}
            a["bars"].append({"orientation": getattr(c, "orientation", None) or "vertical", "label": c.get_label(),
                              "patches": [{"x": p.get_x(), "y": p.get_y(), "w": p.get_width(), "h": p.get_height(),
                                           "fc": rgba(p.get_facecolor())} for p in ps],
                              "datavalues": flist(getattr(c, "datavalues", []) if getattr(c, "datavalues", None) is not None else [])})
    for p in ax.patches:
        if not p.get_visible() or id(p) in bar_ids:
            continue
        if isinstance(p, Rectangle):
            a["rects"].append({"x": p.get_x(), "y": p.get_y(), "w": p.get_width(), "h": p.get_height(), "fc": rgba(p.get_facecolor())})
        elif isinstance(p, (Circle, Ellipse)):
            a["circles"].append({"center": flist(p.center), "width": float(p.width), "height": float(p.height),
                                 "fc": rgba(p.get_facecolor())})
    for l in ax.lines:
        if not l.get_visible():
            continue
        try:
            xy = np.asarray(l.get_xydata(), dtype=float)
        except Exception:
            xy = np.zeros((0, 2))
        a["lines"].append({"x": flist(xy[:, 0]) if len(xy) else [], "y": flist(xy[:, 1]) if len(xy) else [],
                           "color": rgba(l.get_color()), "ls": str(l.get_linestyle()), "lw": float(l.get_linewidth()),
                           "marker": str(l.get_marker()), "label": str(l.get_label()),
                           "transform_is_data": l.get_transform().contains_branch(ax.transData)})
    for col in ax.collections:
        if not col.get_visible():
            continue
        rec = {"type": type(col).__name__, "n_paths": len(col.get_paths()) if hasattr(col, "get_paths") else None}
        try:
            off = np.asarray(col.get_offsets(), dtype=float)
            rec["offsets"] = [flist(off[:, 0]), flist(off[:, 1])] if off.ndim == 2 and len(off) else []
        except Exception:
            rec["offsets"] = []
        try:
            rec["sizes"] = flist(col.get_sizes())
        except Exception:
            rec["sizes"] = []
        try:
            fcs = col.get_facecolors()
            rec["n_fc"] = len(fcs)
            rec["facecolors"] = [rgba(c) for c in fcs[:CAP]]
        except Exception:
            rec["n_fc"], rec["facecolors"] = 0, []
        arr = col.get_array() if hasattr(col, "get_array") else None
        rec["array"] = flist(arr) if arr is not None else None
        rec["cmap"] = cmap_info(col.get_cmap()) if arr is not None else None
        rec["clim"] = flist(col.get_clim()) if arr is not None else None
        if isinstance(col, PathCollection):
            try:
                rec["marker_paths"] = len({str(np.round(p.vertices, 3).tolist()) for p in col.get_paths()})
            except Exception:
                pass
        if isinstance(col, LineCollection):
            rec["segments"] = [[flist(np.asarray(s)[:, 0], 200), flist(np.asarray(s)[:, 1], 200)] for s in col.get_segments()[:200]]
        a["collections"].append(rec)
        for t in getattr(col, "labelTexts", []) or []:
            r = text_rec(t, "clabel", ax_bg)
            if r:
                a["texts"].append(r)
    for im in ax.images:
        if im.get_visible():
            arr = im.get_array()
            a["images"].append({"cmap": cmap_info(im.get_cmap()), "shape": list(np.shape(arr)) if arr is not None else None,
                                "clim": flist(im.get_clim())})
    for t in ax.texts:
        r = text_rec(t, "annotation", ax_bg)
        if r:
            a["texts"].append(r)
    for loc in ("left", "center", "right"):
        r = text_rec(ax._left_title if loc == "left" else ax.title if loc == "center" else ax._right_title, "title", fig_bg)
        if r:
            a["texts"].append(r)
    for lab in (ax.xaxis.label, ax.yaxis.label):
        r = text_rec(lab, "axislabel", fig_bg)
        if r:
            a["texts"].append(r)
    for lab in visible_ticklabels(ax.xaxis) + visible_ticklabels(ax.yaxis):
        r = text_rec(lab, "ticklabel", fig_bg)
        if r:
            a["texts"].append(r)
    for ot in (ax.xaxis.get_offset_text(), ax.yaxis.get_offset_text()):
        r = text_rec(ot, "offset", fig_bg)
        if r:
            a["texts"].append(r)
    leg = ax.get_legend()
    if leg is not None and leg.get_visible():
        lbg = solid_bg(leg.get_frame().get_facecolor(), ax_bg) if leg.get_frame_on() else ax_bg
        for t in leg.get_texts() + [leg.get_title()]:
            r = text_rec(t, "legend", lbg)
            if r:
                a["texts"].append(r)
    return a


def extract(fig, fname, kwargs):
    fc = kwargs.get("facecolor", fig.get_facecolor())
    if kwargs.get("transparent"):
        fc = "white"
    if isinstance(fc, str) and fc == "auto":
        fc = fig.get_facecolor()
    fig_bg = solid_bg(fc, [1.0, 1.0, 1.0, 1.0])
    d = {"fname": str(fname), "basename": os.path.basename(str(fname)), "figsize": flist(fig.get_size_inches()),
         "fig_bg": fig_bg, "axes": [axes_rec(ax, fig_bg) for ax in fig.axes], "fig_texts": []}
    for t in list(fig.texts) + ([fig._suptitle] if getattr(fig, "_suptitle", None) is not None else []) + \
            ([fig._supxlabel] if getattr(fig, "_supxlabel", None) is not None else []) + \
            ([fig._supylabel] if getattr(fig, "_supylabel", None) is not None else []):
        r = text_rec(t, "figtext", fig_bg)
        if r:
            d["fig_texts"].append(r)
    for leg in getattr(fig, "legends", []):
        for t in leg.get_texts():
            r = text_rec(t, "legend", fig_bg)
            if r:
                d["fig_texts"].append(r)
    return d


def patched(self, fname, *args, **kwargs):
    out = _ORIG(self, fname, *args, **kwargs)
    try:
        DUMPS.append(extract(self, fname, kwargs))
    except Exception:
        DUMPS.append({"fname": str(fname), "basename": os.path.basename(str(fname)), "extract_error": traceback.format_exc()[-1500:]})
    return out


def main():
    script, dump = sys.argv[1], sys.argv[2]
    Figure.savefig = patched
    sys.argv = [script]
    err = None
    try:
        runpy.run_path(script, run_name="__main__")
    except SystemExit as e:
        if e.code not in (0, None):
            err = f"SystemExit({e.code})"
    except BaseException:
        err = traceback.format_exc()[-3000:]
    def safe(o):
        try:
            return float(o)
        except Exception:
            return str(o)
    json.dump({"dumps": DUMPS, "error": err}, open(dump, "w"), default=safe)


if __name__ == "__main__":
    main()
