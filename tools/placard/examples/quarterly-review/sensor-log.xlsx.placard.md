---
source: sensor-log.xlsx
source_sha256: 50c8c6826e545c8425a159ef14f68da48fc5635a6b30d894e911476be60e0205
source_bytes: 6860
source_modified: 2026-10-27
tier: standard
confidence: high
placard_version: 2
extractor: docling-2.147.0+models-4.0.4
profile_id: docling-2.147.0+models-4.0.4/text-v1/soffice-present
extracted_at: 2026-11-09T19:43:41
units_kind: worksheet
units_total: 2
units_total_known: true
units_failed: 0
tables_detected: 2
tables_exported: 2
figures_detected: 0
figures_detected_known: true
trim_notes: ""
summary_basis: body-gen
authoring_status: current
body_layout: inline
body_sha256: fabfb797d0614a9dc6c710d741ecc89d92e0c833c27b3e741c49cacfe758a48c
body_bytes: 4080
---

# sensor-log.xlsx — Placard

## What this is
The trial's data workbook: two worksheets, `weekly_readings` (48 rows: 12 weeks by 4 sites)
and `budget_2027` (the cost lines behind the deck's ask).

## Key contents
- weekly_readings (sheet 1): week, site, water_m3, soil_moisture_pct, alerts. Per-site water
  sums equal the report's Table 1 trial totals. The largest alert count in the log is
  Cedar Ridge, week 7: 9 alerts.
- budget_2027 (sheet 2): controllers 200 x $260 = $52,000; filters 200 x $38 = $7,600;
  installation $1,800; total $61,400.

## Distinctive contribution
The only weekly-resolution data (moisture and alerts by week), and the only place the budget
is itemized as a table.

## Open the original if…
- you need cell formats or to recompute from the raw cells; every value is in the body below.

## Gaps / uncertainties
None. Both sheets are fully transcribed.

## Full text
[p.1]
|   week | site         |   water_m3 |   soil_moisture_pct |   alerts |
|--------|--------------|------------|---------------------|----------|
|      1 | Alder Flat   |        331 |                23.2 |        0 |
|      2 | Alder Flat   |        343 |                24.4 |        1 |
|      3 | Alder Flat   |        349 |                24.7 |        2 |
|      4 | Alder Flat   |        337 |                24.2 |        3 |
|      5 | Alder Flat   |        319 |                25.4 |        0 |
|      6 | Alder Flat   |        301 |                25.8 |        1 |
|      7 | Alder Flat   |        295 |                25.3 |        2 |
|      8 | Alder Flat   |        283 |                26.4 |        3 |
|      9 | Alder Flat   |        271 |                26.8 |        0 |
|     10 | Alder Flat   |        265 |                26.3 |        1 |
|     11 | Alder Flat   |        259 |                27.5 |        2 |
|     12 | Alder Flat   |        257 |                27.9 |        3 |
|      1 | Birch Hollow |        368 |                24.7 |        3 |
|      2 | Birch Hollow |        381 |                25.9 |        0 |
|      3 | Birch Hollow |        388 |                26.2 |        1 |
|      4 | Birch Hollow |        374 |                25.8 |        2 |
|      5 | Birch Hollow |        354 |                26.9 |        3 |
|      6 | Birch Hollow |        334 |                27.2 |        0 |
|      7 | Birch Hollow |        327 |                26.8 |        1 |
|      8 | Birch Hollow |        314 |                27.9 |        2 |
|      9 | Birch Hollow |        301 |                28.3 |        3 |
|     10 | Birch Hollow |        294 |                27.8 |        0 |
|     11 | Birch Hollow |        287 |                  29 |        1 |
|     12 | Birch Hollow |        288 |                29.4 |        2 |
|      1 | Cedar Ridge  |        339 |                26.2 |        2 |
|      2 | Cedar Ridge  |        352 |                27.4 |        3 |
|      3 | Cedar Ridge  |        358 |                27.7 |        0 |
|      4 | Cedar Ridge  |        345 |                27.2 |        1 |
|      5 | Cedar Ridge  |        327 |                28.4 |        2 |
|      6 | Cedar Ridge  |        308 |                28.8 |        3 |
|      7 | Cedar Ridge  |        302 |                28.3 |        9 |
|      8 | Cedar Ridge  |        290 |                29.4 |        1 |
|      9 | Cedar Ridge  |        278 |                29.8 |        2 |
|     10 | Cedar Ridge  |        271 |                29.3 |        3 |
|     11 | Cedar Ridge  |        265 |                30.5 |        0 |
|     12 | Cedar Ridge  |        265 |                30.9 |        1 |
|      1 | Dunmore      |        372 |                27.7 |        1 |
|      2 | Dunmore      |        386 |                28.9 |        2 |
|      3 | Dunmore      |        392 |                29.2 |        3 |
|      4 | Dunmore      |        379 |                28.8 |        0 |
|      5 | Dunmore      |        359 |                29.9 |        1 |
|      6 | Dunmore      |        338 |                30.2 |        2 |
|      7 | Dunmore      |        332 |                29.8 |        3 |
|      8 | Dunmore      |        318 |                30.9 |        0 |
|      9 | Dunmore      |        304 |                31.3 |        1 |
|     10 | Dunmore      |        298 |                30.8 |        2 |
|     11 | Dunmore      |        291 |                  32 |        3 |
|     12 | Dunmore      |        291 |                32.4 |        0 |

[p.2]
| item                         |   quantity |   unit_cost_usd |   total_usd |
|------------------------------|------------|-----------------|-------------|
| DC-7 controller              |        200 |             260 |       52000 |
| Inline filter                |        200 |              38 |        7600 |
| Installation (tools, travel) |          1 |            1800 |        1800 |
| Total                        |            |                 |       61400 |
