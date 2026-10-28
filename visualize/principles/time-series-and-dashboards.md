# Time series: dashboard, static figure, or art piece

Shared by both families. Renderers are named only in `registry/renderers.yaml`; ask for one by
property:

    python3 tools/route_renderer.py --shape scalar_time_series --task <task>

Tasks: `live_monitoring`, `exploratory_drilldown`, `many_series_comparison`, `event_annotation`,
`distribution_over_time`, `long_time_series`.

## Which one answers the question

| The question or data | Answer with |
|---|---|
| "What is happening now?" A stream that keeps arriving; alert when it crosses a line | **Live dashboard** over a time-series store |
| "Where in these months, and in which of these hundreds of series, is the odd thing?" | **Exploratory dashboard or store explorer.** Zoom, pan, filter by label; the reader finds the question |
| High-frequency telemetry, millions of samples, many sensors | **Store plus dashboard.** The store aggregates server-side, so the page never holds raw samples |
| A distribution changing over time (speeds across a region, latencies, a spectrum) | **Heatmap of bucketed counts over time**, interactive or as a still |
| One claim about one period, for a slide, paper or report | **Static figure** (CLEAR). A dashboard still makes a poor figure: its chrome, ticks and type are not yours to set |
| Something to feel: a storm's arc, a year of a building's breathing | **Art piece** (BEAUTIFUL). A dark dashboard tops out at handsome, not art |
| Annotated events on a timeline (phases, deployments, launches) | Either. Dashboards hold events as data, but a still shows annotation regions without their text: use a labelled state band |

Rule of thumb: **a dashboard is right when the reader's question is not yet known, or when the data
is not finished arriving.** When the question is known and the data is fixed, make a figure and
capture the dashboard only as a working view.

## Do

- **Pin the query step to the data's cadence** (hourly data → 1 h), at the datasource and on each
  query. Otherwise the step follows panel width, and resizing a panel changes the picture.
- **Keep peaks with a rollup** (`max over the step` for gusts and maxima). By default a step keeps only
  its last sample, so a sub-step spike vanishes.
- **State the sampling rule in the legend** ("last report in hour", "highest gust in hour").
- **Put threshold lines at physical or policy thresholds** (gale force, a service objective), dashed
  and named in the caption. Colour-by-threshold on a line or fill gives the colour break of
  `principles/style.md`.
- **Use a labelled state band for phases.** It survives a still; annotation regions do not.
- **One takeaway per dashboard in CLEAR**, written as a text panel title. A primary question per
  view, even when exploratory.
- **Set the timezone explicitly** (UTC for science data) and write it in the caption.
- **Dashboards as code.** Generate the JSON from a script under version control; never edit in the UI.
- **For historical data, set the store's retention** beyond the data's age before importing.

## Don't

- Don't build a monitoring wall: ten panels with independent y scales invite false cross-panel
  comparison. Share scales by hand when panels are compared.
- Don't use smooth interpolation: it overshoots below zero and above peaks.
- Don't draw circular quantities (direction) as lines; use points, since 360 → 0 draws a false jump.
- Don't let a gap read as continuity. Stores carry the last value forward across short gaps; show
  nulls as gaps.
- Don't trust palette colours by series order; fix every series colour.
- Don't hand a dashboard still to a journal. Make the figure.

## Getting stills and video out

- Stills: kiosk mode plus headless capture, with the viewport as tall as the whole dashboard (panels
  below the fold are lazy and capture empty), device scale 2 for hi-res, and the footer cropped. The
  registry entry lists how; there is no server-side renderer.
- Video: record a scripted walk through the time range. There is no deterministic frame stepping;
  for a movie of a time field, use a renderer that has `deterministic_video`.

## BEAUTIFUL on a dashboard: what is reachable

A dark theme, transparent panels, no titles, a declared rainbow or fire scheme on a heatmap with a
near-black floor, and colour breaks at thresholds get to a handsome working wall. Fonts, axis styling,
tick density and the background stay the tool's. The combined candidate is usually a CLEAR
dashboard for exploration plus a separate art piece made from the same store.

Worked example, both poles: a dashboard study with renders and a colophon, built by a Grafana provisioning script.
