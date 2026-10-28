# Source ledger

Acquired 2026-08-28 via the Fetcher daemon (batch `2026-08-28_vizskilllab_corpus`). Raw text and
PDFs are in `sources/acquired/`; the fetch log is `sources/acquired/FETCH_LOG.txt`. All 28 directives
succeeded. Evidence tiers per the project brief: **A** empirical/peer-reviewed · **B** mature
institutional design practice · **C** canonical expert synthesis · **D** examples/inspiration.

| ID | Source | Canonical URL | Tier | Access | Acquired file |
|----|--------|---------------|------|--------|---------------|
| S01 | Munzner, *Nested Model for Visualization Design and Validation* (2009) | https://www.cs.ubc.ca/labs/imager/tr/2009/NestedModel/ | A | public PDF | `s01_munzner_nested.pdf(.txt)` |
| S02 | Franconeri, Padilla, Shah, Zacks, Hullman, *The Science of Visual Data Communication: What Works* (2021) | https://doi.org/10.1177/15291006211051956 | A | article full text via DOI content negotiation; APS overview public | `004_*.txt`, `003_*.txt`, `005_*.txt` |
| S03 | Rougier, Droettboom, Bourne, *Ten Simple Rules for Better Figures* (2014) | https://doi.org/10.1371/journal.pcbi.1003833 | A | open access (PLOS) | `s03_ten_rules_figures.pdf(.txt)`, `006_*.txt` |
| S04 | Financial Times *Visual Vocabulary* (chart-doctor) | https://github.com/Financial-Times/chart-doctor | B | public repo | `008_*.txt` |
| S05 | Crameri, Shephard, Heron, *The misuse of colour in science communication* (2020) | https://doi.org/10.1038/s41467-020-19160-7 | A | open access, CC BY 4.0 (HTML captured; PDF stub failed) | `009_*.txt` |
| S06 | Nature *Research Figure Guide* | https://research-figure-guide.nature.com/ | B | public web | `011_*.txt`, `012_*.txt` |
| S07 | IBM Design Language: *Data Visualization* | https://www.ibm.com/design/language/data-visualization/ | B | public | `013_*.txt`, `014_*.txt` |
| S08 | IBM Design Language: *Technical Diagrams* | https://www.ibm.com/design/language/infographics/technical-diagrams/ | B | public | `015_*.txt`, `016_*.txt` |
| S09 | Marai, Pinaud, Bühler, Lex, Aerts, *Ten simple rules to create biological network figures for communication* (2019) | https://doi.org/10.1371/journal.pcbi.1007244 | A | open access (PLOS) | `s09_network_figures.pdf(.txt)`, `017_*.txt` |
| S10 | Moritz et al., *Formalizing Visualization Design Knowledge as Constraints* (Draco) | https://idl.uw.edu/papers/draco | A | public paper + repo | `019_*.txt`, `020_*.txt` |
| S11 | Esri, *Primary Design Principles for Cartography* | https://www.esri.com/arcgis-blog/products/arcgis-pro/mapping/primary-design-principles-for-cartography | B | public | `021_*.txt` |
| S12 | NASA Scientific Visualization Studio, *Visualization Principles* | https://svs.gsfc.nasa.gov/gallery/visualization-principles/ | B | public | `022_*.txt` |
| S13 | Datawrapper Academy, *Annotate* | https://academy.datawrapper.de/article/336-annotate-tab | B | public | `023_*.txt` |
| S14 | Jambor, *A checklist for designing and improving the visualization of scientific data* (2025) | https://doi.org/10.1038/s41556-025-01684-z | A | abstract/landing only (subscription) — **reference_only** | `024_*.txt` |
| S15 | Cleveland & McGill, *Graphical Perception* (1984); Heer & Bostock, *Crowdsourcing Graphical Perception* (2010) | https://idl.uw.edu/papers/crowdsourcing-graphical-perception | A | Heer&Bostock abstract public; Cleveland&McGill **reference_only** (JASA paywalled) | `025_*.txt`, `026_*.txt` |
| S16 | W3C, *WCAG 2.2 Understanding: Contrast (Minimum); Use of Color* | https://www.w3.org/WAI/WCAG22/ | A/normative | public | `027_*.txt`, `028_*.txt` |
| C1 | Singh, *Data Visualization Best Practices Using Matplotlib, Seaborn, Plotly* (Medium, 2024) — companion PDF in research dir | (Medium) | D | provided | `companion_singh_*.txt` |
| C2 | *Data Visualization Principles: Master the Essentials!* — companion PDF (no extractable text layer) | (provided) | D | provided, no text | `companion_dataviz_principles_essentials.txt` (empty) |

## Notes on access / integrity

- **S05 Crameri**: the direct `.pdf` link returned a 3 KB stub; the full article HTML was captured
  instead (item 009) and is sufficient for the analysis. CC BY 4.0 permits reuse with attribution.
- **S14 Jambor** and **S15 Cleveland&McGill (1984)** are behind subscription/paywall; marked
  `reference_only`. Their ideas are used only where an accessible Tier-A source corroborates them.
- **C2** companion PDF has no text layer (image-only, 10 KB); treated as absent.
- Reference-only canonical books from the brief (Tufte S17, Few S18, Munzner book S19) were **not**
  acquired (no lawful full text available in-sandbox); their well-known concepts are cross-checked
  against the accessible Tier-A/B sources above and cited as `reference_only` where used.
