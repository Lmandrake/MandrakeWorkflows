---
source: field-trial-report.pdf
source_sha256: 9e8bd07221ac36608e2dc81ff4a1f76248c909e631b5424bd2eb69c7e97c9e5c
source_bytes: 4058
source_modified: 2026-10-27
tier: standard
confidence: high
placard_version: 2
extractor: docling-2.147.0+models-4.0.4
profile_id: docling-2.147.0+models-4.0.4/text-v1/soffice-present
extracted_at: 2026-11-09T19:43:51
units_kind: page
units_total: 5
units_total_known: true
units_failed: 0
tables_detected: 1
tables_exported: 1
figures_detected: 0
figures_detected_known: true
trim_notes: ""
summary_basis: body-gen
authoring_status: current
body_layout: inline
body_sha256: 2b86ec6931512f91be1bf453065c1c64b5a863a2a08f64e2411f62f749732f2e
body_bytes: 2526
---

# field-trial-report.pdf — Placard

## What this is
A five-page field-trial report from Northwind Irrigation Cooperative's operations team on the
DC-7 drip controller, Q3 2026 (6 July to 27 September). It is the written record of the trial
that the review deck presents.

## Key contents
- Scope (p.1): 4 sites, 12 controllers each, 48 units, 12 weeks.
- Headline (p.1): 15,380 m3 used against a 20,000 m3 2025 baseline, a 23.1% reduction; every
  site improved, Cedar Ridge least.
- Method (p.2): baseline is the same plots on fixed timers in 2025; weekly flow-meter reads;
  soil moisture at 30 cm; no weather correction because rainfall was within 8% of 2025.
- Table 1 (p.3): per-site baseline, trial and reduction. Dunmore 27.2% (best), Alder Flat 25.1,
  Birch Hollow 22.0, Cedar Ridge 17.0.
- Problems (p.4): valve stiction at Cedar Ridge, 5 of 12 units, mostly week 7, from hard-water
  scale, cured by an inline filter; clock drift up to 9 minutes a week in firmware 2.3.1,
  fixed by 2.3.4 on 18 August.
- Recommendation (p.5): expand to 200 controllers for 2027, conditional on the filter
  retrofit; board decides 12 November 2026.

## Distinctive contribution
The only file with the method, the rainfall caveat and the firmware fix date. Overlaps the
deck on the headline numbers; carries no costs (those are in the deck and the spreadsheet).

## Open the original if…
- you need the page layout itself; the text and Table 1 are fully in the body below.

## Gaps / uncertainties
None found. The body is the complete text layer; the report has no figures.

## Full text
[p.1]
DC-7 Drip Controller Field Trial, Q3 2026
Summary
Northwind Irrigation Cooperative ran a twelve-week field trial of the DC-7 drip controller from 6 July to 27 September 2026, on four member sites with twelve controllers each (48 units in all).
Across the four sites the trial plots used 15,380 cubic metres of water against a 2025 baseline of 20,000, a reduction of 23.1%. Every site improved; the smallest gain was at Cedar Ridge.
Two problems were found: valve stiction at Cedar Ridge and clock drift in firmware 2.3.1. Both have a fix, described in Section 4.

[p.2]
2. Method
The baseline is the same plots in the 2025 season, irrigated on fixed timers. Flow meters were read weekly by site stewards; soil moisture was logged at 30 cm by one capacitive probe per plot.
Weeks are numbered 1 to 12 from the week of 6 July. Weekly readings, soil moisture and controller alerts are in the companion spreadsheet, sensor-log.xlsx, sheet weekly_readings.
Rainfall during the trial was within 8% of the 2025 season at every site, so no weather correction was applied.

[p.3]
3. Results by site
Table 1. Water use by site, cubic metres.

| Site         |   Units |   Baseline 2025 |   Trial 2026 |   Reduction % |
|--------------|---------|-----------------|--------------|---------------|
| Alder Flat   |      12 |           4,820 |        3,610 |          25.1 |
| Birch Hollow |      12 |           5,140 |        4,010 |          22.0 |
| Cedar Ridge  |      12 |           4,460 |        3,700 |          17.0 |
| Dunmore      |      12 |           5,580 |        4,060 |          27.2 |
| Total        |      48 |          20,000 |       15,380 |          23.1 |
Table 1. Water use by site, cubic metres.
Dunmore gained most (27.2%). Cedar Ridge gained least, and its result is depressed by the valve fault in Section 4.

[p.4]
4. Problems found
Valve stiction. At Cedar Ridge, 5 of the 12 controllers reported a valve that failed to close fully, mostly in week 7. The cause was scale from hard well water. An inline filter cures it; a retrofit is planned for every unit before any expansion.
Clock drift. Firmware 2.3.1 lost up to 9 minutes a week, which shifted watering windows into the afternoon. Firmware 2.3.4, installed on 18 August, fixed it; no drift was seen after that date.

[p.5]
5. Recommendation
Expand to 200 controllers for the 2027 season, conditional on the filter retrofit. The operations board decides at its meeting on 12 November 2026.
Contact for this report: the cooperative's operations team.
