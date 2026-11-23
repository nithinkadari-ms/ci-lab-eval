# Round 4 media tests (repo 2, media/)

Status, 2026-11-21: this file holds the parts that have finished.
- Still being re-run: OCR (gap 1: completion run and extra challengers). Their sections are added when they finish (workflow `media-r4.yml`).
- Datasets and weights were downloaded inside the jobs and never committed.

## Word formulas: real Word / Cambria Math

**Data:**
- **Real Word set:** 300 generated OMML .docx files with 1,200 equations (each construct about 63 times; 272 inline, 928 display).
  - Exported to PDF by Microsoft Word 16.0 (build 18526) through COM.
  - Every PDF embeds a CambriaMath subset.
  - Release `word-pdf-v1`; generator `media/wordmath/wordset.py`.
- **Windows set:** 2,000 formulas of the same kinds, rendered on windows-latest by LuaLaTeX + unicode-math with Cambria Math (`C:/Windows/Fonts/cambria.ttc`). 0 LaTeX errors.

**Gold and scoring:**
- Gold = the source OMML as LaTeX, with all accepted forms. A parenthesised no-bar fraction also accepts `\binom`.
- Normalised with the round-3 normaliser. Equation numbers are stripped on both sides.
- Exact = the normalised strings are equal. Edit = 1 - normalised Levenshtein distance.

**Arms:**
- the round-3 glyph logic, unchanged;
- Pix2Text MFR 1.5 int8 with decoder cap 1024, on 3x crops;
- logic + fallback: the logic result is kept when its confidence >= tau, otherwise Pix2Text's. tau is chosen on the dev half of each set.

**Runs:** generation 44882473997; scoring 44885136296 (8 shards, no errors). The tables below were re-aggregated after two gold fixes: `\binom` accepted, and spaced equation numbers stripped.

- real Word (Cambria Math): 1200 formulas, errors {}; gate tau (dev half) = 0.9; fonts in regions: CambriaMath (1200); mean share of Unicode math alphanumerics among region glyphs 0.40.
- Windows LuaLaTeX + Cambria Math: 2000 formulas, errors {}; gate tau (dev half) = 0.9; fonts in regions: CambriaMath (2000), Cambria (558); mean share of Unicode math alphanumerics among region glyphs 0.38.

Held-out half (tau chosen on the other half):

| set | n | logic exact | model exact | logic+fallback exact | logic coverage | logic exact on accepted | hybrid vs model (better / worse, p) |
|---|---|---|---|---|---|---|---|
| real Word (Cambria Math) | 615 | 51.7% | 63.1% | **62.8%** | 74.5% | 69.4% | 64 / 66, p = 0.930 |
| Windows LuaLaTeX + Cambria Math | 1028 | 41.5% | 66.7% | **67.7%** | 51.3% | 80.8% | 61 / 51, p = 0.395 |

Per construct, all formulas (exact % / edit score); columns per set:

| construct | word: n | word: logic | word: model | word: logic+fallback | word: coverage | win: n | win: logic | win: model | win: logic+fallback | win: coverage |
|---|---|---|---|---|---|---|---|---|---|---|
| accent | 63 | 100.0 / 1.000 | 92.1 / 0.956 | 100.0 / 1.000 | 100% | 105 | 100.0 / 1.000 | 84.8 / 0.932 | 100.0 / 1.000 | 100% |
| bar | 63 | 38.1 / 0.677 | 82.5 / 0.960 | 38.1 / 0.677 | 98% | 105 | 41.9 / 0.692 | 81.9 / 0.946 | 42.9 / 0.700 | 96% |
| binomial | 64 | 54.7 / 0.751 | 65.6 / 0.870 | 54.7 / 0.754 | 97% | 106 | 0.0 / 0.365 | 38.7 / 0.731 | 38.7 / 0.728 | 3% |
| delimiter | 63 | 71.4 / 0.893 | 69.8 / 0.916 | 74.6 / 0.908 | 92% | 105 | 49.5 / 0.821 | 69.5 / 0.903 | 78.1 / 0.934 | 52% |
| eqarray | 63 | 41.3 / 0.799 | 63.5 / 0.927 | 69.8 / 0.932 | 56% | 105 | 33.3 / 0.775 | 47.6 / 0.862 | 49.5 / 0.861 | 41% |
| eqnumber | 63 | 76.2 / 0.930 | 81.0 / 0.948 | 79.4 / 0.941 | 90% | 105 | 64.8 / 0.866 | 71.4 / 0.926 | 75.2 / 0.923 | 70% |
| fraction | 64 | 25.0 / 0.863 | 50.0 / 0.901 | 48.4 / 0.885 | 45% | 106 | 45.3 / 0.800 | 59.4 / 0.886 | 60.4 / 0.885 | 61% |
| function | 63 | 95.2 / 0.984 | 95.2 / 0.988 | 95.2 / 0.984 | 100% | 105 | 89.5 / 0.968 | 92.4 / 0.972 | 95.2 / 0.983 | 94% |
| limit | 63 | 27.0 / 0.810 | 65.1 / 0.926 | 66.7 / 0.944 | 41% | 105 | 39.0 / 0.805 | 87.6 / 0.970 | 90.5 / 0.972 | 41% |
| long | 63 | 27.0 / 0.874 | 38.1 / 0.891 | 33.3 / 0.880 | 54% | 105 | 15.2 / 0.843 | 45.7 / 0.919 | 43.8 / 0.919 | 23% |
| matrix | 63 | 55.6 / 0.853 | 58.7 / 0.877 | 65.1 / 0.893 | 70% | 105 | 10.5 / 0.572 | 76.2 / 0.957 | 76.2 / 0.957 | 11% |
| nary | 63 | 61.9 / 0.885 | 66.7 / 0.926 | 68.3 / 0.918 | 79% | 105 | 20.0 / 0.763 | 80.0 / 0.959 | 80.0 / 0.958 | 23% |
| nested | 63 | 61.9 / 0.942 | 74.6 / 0.948 | 76.2 / 0.957 | 76% | 105 | 0.0 / 0.874 | 73.3 / 0.926 | 73.3 / 0.926 | 0% |
| prescript | 63 | 74.6 / 0.883 | 27.0 / 0.705 | 74.6 / 0.880 | 90% | 105 | 74.3 / 0.899 | 36.2 / 0.780 | 75.2 / 0.911 | 85% |
| radical | 63 | 36.5 / 0.810 | 36.5 / 0.797 | 41.3 / 0.832 | 84% | 105 | 28.6 / 0.766 | 41.9 / 0.815 | 43.8 / 0.853 | 44% |
| subscript | 63 | 55.6 / 0.850 | 65.1 / 0.933 | 61.9 / 0.920 | 79% | 106 | 60.4 / 0.864 | 69.8 / 0.904 | 65.1 / 0.896 | 79% |
| subsup | 63 | 65.1 / 0.869 | 73.0 / 0.884 | 66.7 / 0.883 | 89% | 106 | 70.8 / 0.880 | 84.9 / 0.945 | 79.2 / 0.926 | 82% |
| superscript | 64 | 53.1 / 0.822 | 62.5 / 0.890 | 56.2 / 0.854 | 83% | 106 | 58.5 / 0.844 | 74.5 / 0.913 | 67.9 / 0.892 | 82% |
| underbrace | 63 | 0.0 / 0.353 | 60.3 / 0.848 | 60.3 / 0.848 | 0% | 105 | 0.0 / 0.242 | 71.4 / 0.906 | 71.4 / 0.906 | 0% |
| inline | 272 | 56.2 / 0.844 | 58.8 / 0.885 | 63.6 / 0.876 | 81% | 401 | 58.1 / 0.821 | 69.6 / 0.902 | 71.1 / 0.894 | 75% |
| display | 928 | 52.9 / 0.831 | 66.3 / 0.903 | 65.1 / 0.892 | 73% | 1599 | 38.2 / 0.758 | 67.3 / 0.903 | 68.2 / 0.904 | 46% |
| ALL | 1200 | 53.7 / 0.834 | 64.6 / 0.899 | 64.8 / 0.889 | 75% | 2000 | 42.2 / 0.770 | 67.8 / 0.903 | 68.8 / 0.902 | 52% |

- real Word (Cambria Math): logic median 0.7 ms, Pix2Text int8 median 327 ms (4 threads), decoder runaways 0.
- Windows LuaLaTeX + Cambria Math: logic median 0.7 ms, Pix2Text int8 median 375 ms (4 threads), decoder runaways 0.

**Verdict, gap 11 (Word PDFs with Cambria Math):**
- **Pix2Text is the better primary engine on Word PDFs.**
  - Real Word: 64.6% exact vs 53.7% for the logic.
  - Windows render: 67.8% vs 42.2%.
- **The round-3 gate adds nothing significant on top of Pix2Text:**
  - real Word held-out: 62.8% vs 63.1%, p = 0.93;
  - Windows held-out: 67.7% vs 66.7%, p = 0.40.
- **The logic is clearly better only on two constructs:** accents (100% vs 92%) and prescripts (75% vs 27%).
- **The logic fails on:**
  - underbraces (0%), because it doesn't build `\underbrace`;
  - underlines, which come out as overlines;
  - `\lim` with the limit below;
  - fractions with tall parts;
  - matrices and n-ary operators in the LuaLaTeX set.
- **Decision:** for Word-made PDFs, send Cambria Math regions to Pix2Text by default and keep the logic only for accent and prescript patterns. Or fix the logic gaps above and re-test.
- The LibreOffice math-font result is not used for decisions.

## Gap 2. Charts

**Runs:**
- Main run: 44881551040 (`media-r4.yml`, part=charts). 0 errors in every arm.
  - Vector, synthetic PDFs: 513 scored + 87 abstained.
  - Raster renders: 528/540/440 scored of 600 each (100 dpi / 150 dpi / JPEG).
  - ChartX: 413 + 739 abstained.
  - DePlot: 700 scored.
- **PlotQA is being re-scored** in run 44920588794 (`charts-plotqa-r4.yml`).
  - The achang/plot_qa repack stores categorical x as indices 0..n-1, without the tick labels. Name-keyed RMS was therefore ~0 for every method, including DePlot: 0.042, with 227 of 250 at zero.
  - PlotQA is now compared by point position. Its rows are left out below until that run reports.

RMS = DePlot's relative mapping similarity F1 (keys `x series`, number_theta 0.1); `all` counts abstentions as 0, `covered` only charts the method answered; `names ignored` matches series by assignment instead of name. Synthetic charts also report the share of true points recovered and within 1% / 5% relative error (series matched by colour, points by category), and point F1 (2% of axis range) for scatter plots.

### 2a. Vector charts (synthetic PDFs) vs raster tracing of the same charts

| slice | charts | coverage | RMS-F1 all | RMS-F1 covered | RMS-F1 names ignored | points found | within 1% | within 5% | scatter point F1 | median ms |
|---|---|---|---|---|---|---|---|---|---|---|
| vector (all types) | 600 | 0.855 | 0.505 | 0.591 | 0.602 | 0.927 | 0.868 | 0.874 | 0.000 | 11 |
| raster_150 (all types) | 600 | 0.900 | 0.538 | 0.598 | 0.685 | 0.435 | 0.219 | 0.351 | 0.980 | 725 |
| raster_100 (all types) | 600 | 0.880 | 0.503 | 0.572 | 0.634 | 0.611 | 0.198 | 0.466 | 0.967 | 525 |
| raster_jpeg (all types) | 600 | 0.733 | 0.318 | 0.434 | 0.397 | 0.375 | 0.083 | 0.255 | 0.477 | 521 |
| vector: bar | 60 | 1.000 | 0.808 | 0.808 | 0.836 | 0.869 | 0.795 | 0.795 | - | 9 |
| raster_150: bar | 60 | 1.000 | 0.780 | 0.780 | 0.941 | 0.884 | 0.507 | 0.749 | - | 779 |
| vector: dense_line | 60 | 1.000 | 0.038 | 0.038 | 0.166 | 1.000 | 1.000 | 1.000 | - | 26 |
| raster_150: dense_line | 60 | 1.000 | 0.134 | 0.134 | 0.173 | 0.022 | 0.002 | 0.013 | - | 665 |
| vector: grouped_bar | 60 | 1.000 | 0.887 | 0.887 | 0.892 | 0.868 | 0.783 | 0.785 | - | 13 |
| raster_150: grouped_bar | 60 | 0.983 | 0.715 | 0.727 | 0.859 | 0.877 | 0.384 | 0.701 | - | 756 |
| vector: hbar | 60 | 1.000 | 0.943 | 0.943 | 0.983 | 1.000 | 0.990 | 0.990 | - | 9 |
| raster_150: hbar | 60 | 1.000 | 0.784 | 0.784 | 0.933 | 0.919 | 0.589 | 0.760 | - | 772 |
| vector: line | 60 | 0.933 | 0.142 | 0.152 | 0.707 | 0.771 | 0.692 | 0.692 | - | 9 |
| raster_150: line | 60 | 0.900 | 0.644 | 0.716 | 0.781 | 0.901 | 0.517 | 0.746 | - | 760 |
| vector: line_markers | 60 | 0.767 | 0.603 | 0.786 | 0.638 | 0.794 | 0.715 | 0.718 | - | 15 |
| raster_150: line_markers | 60 | 0.983 | 0.639 | 0.650 | 0.887 | 0.940 | 0.633 | 0.775 | - | 746 |
| vector: log_line | 60 | 0.900 | 0.081 | 0.090 | 0.237 | 0.809 | 0.300 | 0.399 | - | 10 |
| raster_150: log_line | 60 | 0.167 | 0.006 | 0.037 | 0.027 | 0.986 | 0.042 | 0.127 | - | 723 |
| vector: neg_bar | 60 | 0.850 | 0.699 | 0.822 | 0.725 | 0.858 | 0.777 | 0.782 | - | 9 |
| raster_150: neg_bar | 60 | 0.983 | 0.722 | 0.735 | 0.855 | 0.892 | 0.545 | 0.796 | - | 716 |
| vector: scatter | 60 | 0.100 | 0.000 | 0.000 | 0.000 | - | - | - | 0.000 | 20 |
| raster_150: scatter | 60 | 1.000 | 0.375 | 0.375 | 0.489 | - | - | - | 0.980 | 857 |
| vector: stacked_bar | 60 | 1.000 | 0.849 | 0.849 | 0.834 | 0.880 | 0.800 | 0.802 | - | 12 |
| raster_150: stacked_bar | 60 | 0.983 | 0.577 | 0.587 | 0.903 | 0.884 | 0.314 | 0.711 | - | 629 |

Vector vs raster (150 dpi) on the same 600 charts, per-chart RMS-F1: vector better 241, worse 270, p = 0.215.

Abstention reasons (vector): no marks: 54, no series: 24, bars without a calibrated value axis: 9

### 2b. Raster charts from datasets

| slice | charts | coverage | RMS-F1 all | RMS-F1 covered | RMS-F1 names ignored | points found | within 1% | within 5% | scatter point F1 | median ms |
|---|---|---|---|---|---|---|---|---|---|---|
| chartx all | 1152 | 0.359 | 0.100 | 0.278 | 0.152 | - | - | - | - | 322 |
| chartx supported types | 650 | 0.609 | 0.176 | 0.289 | 0.269 | - | - | - | - | 592 |
| chartx: bar_chart | 100 | 0.820 | 0.420 | 0.513 | 0.499 | - | - | - | - | 710 |
| chartx: line_chart | 100 | 0.770 | 0.307 | 0.398 | 0.515 | - | - | - | - | 767 |
| chartx: pie_chart | 100 | 0.020 | 0.000 | 0.000 | 0.000 | - | - | - | - | 22 |
| chartx: bar_chart_num | 100 | 0.660 | 0.338 | 0.511 | 0.462 | - | - | - | - | 582 |
| chartx: line_chart_num | 100 | 0.130 | 0.039 | 0.304 | 0.071 | - | - | - | - | 25 |
| chartx: heatmap | 52 | 0.000 | 0.000 | - | 0.000 | - | - | - | - | 21 |
| chartx: rings | 50 | 0.000 | 0.000 | - | 0.000 | - | - | - | - | 22 |
| chartx: rose | 50 | 0.000 | 0.000 | - | 0.000 | - | - | - | - | 24 |
| chartx: area_chart | 50 | 0.920 | 0.013 | 0.014 | 0.061 | - | - | - | - | 837 |
| chartx: 3D-Bar | 50 | 0.020 | 0.000 | 0.000 | 0.000 | - | - | - | - | 23 |
| chartx: box | 50 | 0.200 | 0.002 | 0.012 | 0.011 | - | - | - | - | 708 |
| chartx: bubble | 50 | 0.940 | 0.001 | 0.001 | 0.002 | - | - | - | - | 1026 |
| chartx: candlestick | 50 | 0.000 | 0.000 | - | 0.000 | - | - | - | - | 39 |
| chartx: funnel | 50 | 0.000 | 0.000 | - | 0.000 | - | - | - | - | 14 |

### 2c. DePlot (google/deplot, ~1.1 GB, offline reference) vs our tracing on the same charts

| set | charts | DePlot RMS-F1 | ours RMS-F1 (abstain = 0) | ours coverage | ours better | DePlot better | p | DePlot median s/chart |
|---|---|---|---|---|---|---|---|---|
| synth | 200 | 0.327 | 0.546 | 0.890 | 103 | 61 | 0.001 | 48.7 |
| chartx | 250 | 0.693 | 0.356 | 0.768 | 42 | 193 | 2.6e-24 | 45.8 |

**PlotQA (re-scored in run 44920588794; 0 errors: 604 scored + 396 abstained for ours, 250 for DePlot):**
- Even keyed by point position, every method stays near zero: DePlot RMS-F1 0.069, ours 0.002 (names ignored 0.072).
- DePlot was trained on PlotQA, so this means the achang/plot_qa repack's value encoding does not match what the rendered charts show. Its x values are indices, and its y values are raw source numbers while the axes show scaled ticks.
- **PlotQA is therefore excluded as unusable ground truth.** The raster verdict rests on ChartX and the synthetic set.

**Verdict, gap 2:**
- **Vector charts (ChartDetective-style, our code): adopt for bar-type charts.**
  - Bar, grouped, stacked, horizontal and negative bars: coverage 85-100%, RMS-F1 0.70-0.94, 78-99% of points within 1%. About 11 ms per chart, no model.
  - Line charts: the values are right (69-100% of points within 1%), but the series names are lost. Legend parsing for line swatches fails, so name-keyed RMS is only 0.14 vs 0.71 with names ignored. Dense numeric-x lines also lose RMS because x is printed with full precision.
  - Scatter (10% coverage, markers not found) and log axes (30% within 1%) need work before shipping.
- **Raster tracing (figrecover-style + PP-OCRv6 ticks): not good enough for values.**
  - Only 22% of points within 1% and 35% within 5% at 150 dpi; JPEG renders are worse. Log axes are mostly abstained.
  - Per-chart RMS ties the vector route (p = 0.22), but value precision is far lower.
- **DePlot (1.1 GB, about 50 s per chart on CPU):**
  - Clearly better on real raster charts: ChartX 0.693 vs 0.356, p = 2.6e-24.
  - Worse on our synthetic charts (0.327 vs 0.546), since it doesn't output our series and keys.
  - Too large and slow to ship. It remains an offline reference.
- **Recommendation:** ship vector extraction for bars now, with an abstain path. Fix line legends, scatter markers and log axes, then re-test. For raster charts, keep the image plus caption and expose no numbers (or only flagged low-confidence ones).

## Word formulas: DOCX (OMML) and the LibreOffice PDF route

751 equations (31 hand-written OMML with hand LaTeX, the rest generated from one AST into OMML + gold LaTeX + gold MathML). easydoc-math scored by normalised LaTeX against the gold forms; omml2mml.xsl scored by canonical MathML skeleton (generated cases only, hand cases have no MathML gold); PDF route = LibreOffice export + round-3 glyph logic.

| construct | n | easydoc-math exact | easydoc errors | omml2mml.xsl skeleton exact | PDF glyph rebuild exact |
|---|---|---|---|---|---|
| fraction | 43 | 0.372 | 0 | 0.850 | 0.628 |
| binomial | 41 | 0.902 | 0 | 0.975 | 0.000 |
| superscript | 41 | 0.439 | 0 | 0.975 | 0.659 |
| subscript | 41 | 0.341 | 0 | 0.975 | 0.561 |
| subsup | 41 | 0.756 | 0 | 1.000 | 0.756 |
| prescript | 41 | 0.000 | 0 | 0.975 | 0.683 |
| nary | 43 | 0.349 | 0 | 1.000 | 0.535 |
| radical | 42 | 0.643 | 0 | 0.425 | 0.381 |
| matrix | 43 | 0.698 | 0 | 0.975 | 0.047 |
| eqarray | 41 | 0.244 | 0 | 0.875 | 0.390 |
| accent | 44 | 1.000 | 0 | 1.000 | 0.750 |
| bar | 42 | 0.929 | 0 | 0.975 | 0.381 |
| delimiter | 42 | 0.405 | 0 | 0.975 | 0.667 |
| function | 42 | 0.881 | 0 | 1.000 | 0.929 |
| limit | 41 | 0.000 | 0 | 0.900 | 0.146 |
| underbrace | 41 | 0.488 | 0 | 0.950 | 0.000 |
| eqnumber | 41 | 0.000 | 0 | 1.000 | 0.000 |
| nested | 41 | 0.854 | 0 | 0.000 | 0.634 |
| **all** | 751 | **0.519** | 0 | **0.879** | **0.454** |

Hand-written cases only: easydoc-math 23/31, PDF route 20/31.
Equation numbers kept: easydoc-math 41/41, omml2mml.xsl 40/41, PDF route 0/41.
easydoc-math vs omml2mml.xsl on the same 720 generated equations: easydoc right and XSLT wrong 50, the reverse 316, sign test p = 2.3e-48 (different output formats, see method).
PDF fonts seen in equation regions: LiberationSerif-Italic (705), OpenSymbol (622), LiberationSerif (569).
LibreOffice export 1.0 s per 25-equation DOCX.
Speed: easydoc-math 85 us/equation in the Rust binary (process total 0.07 s for 751); XSLT 0.35 ms/equation.

Notes:
- The PDF column uses LibreOffice's math fonts (LiberationSerif, OpenSymbol), not Cambria Math, and is not used for decisions; see the real-Word section above.
- From the DOCX XML itself:
  - omml2mml.xsl (BSD-2) reproduces the MathML structure for 87.9% of generated equations;
  - easydoc-math 0.1.2 gets 51.9% exact LaTeX: weak on prescripts, limits and equation numbers (0%), and on fractions with scripts.
- **Pick:** for DOCX input, read OMML with the XSLT-style mapping (or port its rules to Rust) rather than easydoc-math as it stands.

## Gap 3. Forms without fillable fields

**Run:** 44898133792 (`media-r4.yml`, part=nocharts); the `forms` and `ffdetr` jobs succeeded.

**Inputs checked:**
- `run_forms.py` and `ffdetr_match.py` run their own PP-OCRv6 small detection + recognition on the FUNSD and generated-form images inside the forms job.
- They do not use the `ocr-pages` outputs, so the timed-out OCR jobs do not affect these numbers.

### 3a. Label -> value matcher (FUNSD test, 50 forms, PP-OCRv6 small boxes)

OCR lines: 2566; mapped to an entity: 2444; question->answer links: 837; blank questions: 477. Thresholds picked on half of the training forms: geo -1.25, geo_lilt -1.00.

| method | pair P | pair R | pair F1 | exact value P / R | blanks wrongly filled | repeated-label P / R |
|---|---|---|---|---|---|---|
| nn | 0.485 | 0.302 | 0.372 | 0.241 / 0.151 | 0.203 | 0.448 / 0.184 |
| nn_lilt | 0.554 | 0.432 | 0.486 | 0.291 / 0.227 | 0.203 | 0.766 / 0.322 |
| geo | 0.524 | 0.397 | 0.452 | 0.259 / 0.196 | 0.136 | 0.636 / 0.294 |
| geo_lilt | 0.820 | 0.450 | 0.581 | 0.422 / 0.232 | 0.055 | 0.931 / 0.373 |

Paired per-form F1 (sign test):

| A vs B | A better | B better | p |
|---|---|---|---|
| geo vs nn | 32 | 10 | 9.4e-04 |
| geo vs nn_lilt | 20 | 24 | 0.652 |
| geo_lilt vs geo | 36 | 8 | 2.5e-05 |
| geo_lilt vs nn_lilt | 38 | 7 | 3.1e-06 |

Time: OCR 1.50 s/form; LiLT 0.23 s/form (CPU, 521 MB fp32 checkpoint); geometry matcher < 5 ms/form.

EC-FUNSD and DocILE: not used (no EC-FUNSD release on the Hugging Face hub when checked on 2026-11-21; DocILE data is gated behind a research-access request).

**Verdict, gap 3:**
- **The geometry + type matcher with Hungarian assignment** clearly beats nearest-neighbour:
  - pair F1 0.452 vs 0.372, 32 vs 10 forms, p = 9.4e-4;
  - it also wrongly fills fewer blank fields (13.6% vs 20.3%).
- **Adding LiLT's question/answer probabilities as features (geo_lilt)** is the best variant:
  - pair F1 0.581, precision 0.820, only 5.5% of blanks filled, 93% precision on repeated labels;
  - better than geo alone (36 vs 8 forms, p = 2.5e-5) and than LiLT + nearest-neighbour (38 vs 7, p = 3.1e-6).
  - But LiLT is a 521 MB fp32 checkpoint (0.23 s per form on CPU).
- **Pick:** ship the pure geometry matcher (no model, under 5 ms per form) as the default. Treat LiLT typing as an optional quality mode if a smaller (INT8, about 130 MB) export validates.
- Recall stays low (0.40-0.45) because FUNSD links are often multi-line or table-like values.

## Forms: FFDetr

Test only, not a replacement.
- **Code:** commonforms 0.2.1 inference logic, run through rfdetr 1.12.1 (Apache-2.0). commonforms itself has no licence file and depends on ultralytics (AGPL), so it was not installed.
- **Checkpoints:** jbarrow/FFDetr@56f4e42 and pdf-net/ffdetr-filled@186c904. Both cards say apache-2.0; neither repo has a LICENSE file. 135 MB each.

Checkpoints: jbarrow/FFDetr@56f4e42 and pdf-net/ffdetr-filled@186c904 (model cards: apache-2.0; repos ship no separate LICENSE file). Matching at IoU 0.5 with the same class unless noted.

### Generated flattened forms (gold = AcroForm widgets before flattening)

| model | variant | field type | P | R | F1 | gold |
|---|---|---|---|---|---|---|
| ffdetr | empty | TextBox | 0.890 | 0.963 | 0.925 | 1760 |
| ffdetr | empty | ChoiceButton | 1.000 | 0.961 | 0.980 | 770 |
| ffdetr | empty | Signature | 0.000 | 0.000 | 0.000 | 154 |
| ffdetr | empty | any class | 0.978 | 0.963 | 0.970 | 2684 |
| ffdetr | filled | TextBox | 0.740 | 0.430 | 0.544 | 1760 |
| ffdetr | filled | ChoiceButton | 1.000 | 0.369 | 0.539 | 770 |
| ffdetr | filled | Signature | 0.000 | 0.000 | 0.000 | 154 |
| ffdetr | filled | any class | 0.879 | 0.428 | 0.576 | 2684 |
| ffdetr | filled_scan | TextBox | 0.692 | 0.315 | 0.433 | 1760 |
| ffdetr | filled_scan | ChoiceButton | 1.000 | 0.138 | 0.242 | 770 |
| ffdetr | filled_scan | Signature | 0.000 | 0.000 | 0.000 | 154 |
| ffdetr | filled_scan | any class | 0.825 | 0.279 | 0.417 | 2684 |
| ffdetr_filled | empty | TextBox | 0.882 | 0.945 | 0.913 | 1760 |
| ffdetr_filled | empty | ChoiceButton | 0.999 | 0.951 | 0.974 | 770 |
| ffdetr_filled | empty | Signature | 0.800 | 0.026 | 0.050 | 154 |
| ffdetr_filled | empty | any class | 0.972 | 0.950 | 0.961 | 2684 |
| ffdetr_filled | filled | TextBox | 0.842 | 0.589 | 0.693 | 1760 |
| ffdetr_filled | filled | ChoiceButton | 0.990 | 0.739 | 0.846 | 770 |
| ffdetr_filled | filled | Signature | 0.667 | 0.013 | 0.025 | 154 |
| ffdetr_filled | filled | any class | 0.941 | 0.634 | 0.758 | 2684 |
| ffdetr_filled | filled_scan | TextBox | 0.843 | 0.484 | 0.615 | 1760 |
| ffdetr_filled | filled_scan | ChoiceButton | 1.000 | 0.631 | 0.774 | 770 |
| ffdetr_filled | filled_scan | Signature | 0.800 | 0.026 | 0.050 | 154 |
| ffdetr_filled | filled_scan | any class | 0.952 | 0.533 | 0.683 | 2684 |

Checkbox state (ink share inside the detected box > 0.06; FFDetr itself has no checked/unchecked class):

- ffdetr: empty 735/740 (0.993), filled 282/284 (0.993), filled_scan 104/106 (0.981); same rule on the gold boxes: 1540/1540
- ffdetr_filled: empty 720/732 (0.984), filled 565/569 (0.993), filled_scan 483/486 (0.994); same rule on the gold boxes: 1540/1540

### FUNSD (no widget boxes: answer entities used as value regions)

| model | answers covered (recall proxy) | TextBox boxes on an answer (precision proxy) | TextBox boxes on a question label |
|---|---|---|---|
| ffdetr | 31/3623 = 0.009 | 36/1224 = 0.029 | 2/1224 = 0.002 |
| ffdetr_filled | 538/3623 = 0.148 | 538/2027 = 0.265 | 39/2027 = 0.019 |

### Signatures (SignverOD, 250 scanned pages with signatures, IoU 0.3)

| model | P | R | F1 |
|---|---|---|---|
| ffdetr | 0.000 | 0.000 | 0.000 |
| ffdetr_filled | 0.000 | 0.000 | 0.000 |

CPU time per page (4 threads, torch CPU, includes pre/post-processing): ffdetr p50 531 ms (135 MB checkpoint), ffdetr_filled p50 553 ms (135 MB checkpoint)

### FFDetr boxes as value regions for the label->value matcher (vs OCR lines only)

FUNSD (50 test forms, entity-level pairs):

| value regions | pair P | pair R | pair F1 | forms better / worse vs OCR only | p |
|---|---|---|---|---|---|
| OCR lines only | 0.524 | 0.397 | 0.452 | - | - |
| ffdetr TextBox boxes | 0.500 | 0.002 | 0.005 | 0 / 46 | 2.8e-14 |
| ffdetr_filled TextBox boxes | 0.336 | 0.057 | 0.098 | 1 / 45 | 1.3e-12 |

Generated flattened forms (test templates):

| variant | gold pairs | value regions | pair P | pair R | pair F1 | forms better / worse vs OCR only | p |
|---|---|---|---|---|---|---|---|
| empty | all fields | OCR lines only | - | 0.000 | - | - | - |
| empty | all fields | ffdetr boxes | 0.934 | 0.604 | 0.733 | - | - |
| empty | all fields | ffdetr_filled boxes | 0.935 | 0.591 | 0.724 | - | - |
| filled | filled fields | OCR lines only | 0.939 | 0.820 | 0.875 | - | - |
| filled | filled fields | ffdetr boxes | 0.710 | 0.246 | 0.365 | 1 / 107 | 6.7e-31 |
| filled | filled fields | ffdetr_filled boxes | 0.855 | 0.390 | 0.536 | 11 / 90 | 1.4e-16 |
| filled | all fields | OCR lines only | 0.929 | 0.463 | 0.618 | - | - |
| filled | all fields | ffdetr boxes | 0.811 | 0.242 | 0.372 | 21 / 88 | 6.1e-11 |
| filled | all fields | ffdetr_filled boxes | 0.865 | 0.325 | 0.473 | 34 / 70 | 5.3e-04 |
| filled_scan | filled fields | OCR lines only | 0.904 | 0.829 | 0.865 | - | - |
| filled_scan | filled fields | ffdetr boxes | 0.709 | 0.182 | 0.289 | 3 / 107 | 3.4e-28 |
| filled_scan | filled fields | ffdetr_filled boxes | 0.838 | 0.306 | 0.448 | 7 / 99 | 6.5e-22 |
| filled_scan | all fields | OCR lines only | 0.904 | 0.468 | 0.616 | - | - |
| filled_scan | all fields | ffdetr boxes | 0.825 | 0.198 | 0.320 | 15 / 91 | 1.9e-14 |
| filled_scan | all fields | ffdetr_filled boxes | 0.888 | 0.265 | 0.408 | 27 / 81 | 1.9e-07 |

**Verdict, FFDetr:**
- **Good empty-field detector, poor filled-form detector:**
  - empty generated forms: text fields F1 0.91-0.93, checkboxes 0.97-0.98;
  - filled forms: base model F1 0.54 (filled_scan 0.43); the filled-form fine-tune 0.69 (0.62) for text fields and 0.85 (0.77) for checkboxes.
- **Signatures:** almost never detected (F1 <= 0.05 on generated signature fields, 0 on SignverOD's handwritten signatures).
- **FUNSD:** it marks only 0.9-15% of filled answers.
- **Checkbox state** from the ink inside the detected box is reliable: 98-99%.
- **As value regions for the matcher, it lowers pair F1 everywhere except empty forms:**
  - filled generated forms: 0.54 vs 0.875 with OCR lines;
  - FUNSD: 0.10 vs 0.45.
  - On empty forms it is the only way to pair labels with blank fields: F1 0.73, where OCR-only gets nothing.
- **Use:** only as an optional "find blank fields and checkboxes" step on empty or flattened templates, never as the value source on filled forms. About 0.55 s per page on CPU.

## OCR: extra challengers

Tests only.
- **Run:** 45140140168 (`ocr-extra-r4.yml`), 14 jobs, all green.
- **Per-item files checked:** 693 pages, 31,685 line crops, 0 page errors.
  - UnionST: 693 pages with every arm (v6s, whole line, word-split, second-reader merge).
  - UniRec: 347 pages.
  - DocRes: 36 gated or forced pages.
  - Crop counts match between jobs; PP-OCRv6 medium on the same crops was matched for 635 pages.
- **Sampling flaw (preliminary results):** taking every 4th (8th) page of the page list aliased with the 8 degradations per synthetic base document. The synthetic part therefore holds only the `lowdpi` and `curved` pages (UniRec: only `curved`), and DocRes never saw blurred, faded or noisy pages.
- A stratified rerun (all 8 degradations of every 4th / 8th base document) replaces the per-defect tables when it reports. The overall conclusions below are unlikely to change: every challenger loses to PP-OCRv6 small on almost every document.
- **Models and memory:**
  - UnionST-SP: 97.6 MB, MIT per the card but no LICENSE file; OpenOCR code Apache-2.0. Process RSS 1.71 GB with PP-OCRv6 small.
  - UniRec-0.1B: ONNX fp32, 719 MB, Apache card; 1.99 GB RSS.
  - DocRes: 183 MB, MIT code, tiled float32 on CPU; 1.63 GB RSS.
  - CPU per line crop (4 threads): v6s 24 ms, UnionST line 65 ms, UnionST word-split 173 ms, UniRec 357 ms. DocRes 141-425 s per page.

Same pages and the same PP-OCRv6 small detector crops as the main OCR test (UnionST and DocRes: every 4th page; UniRec: every 8th page). Pages with records: 693, line crops: 31685, page errors 0, crop-count mismatches between jobs 0. PP-OCRv6 medium on the same crops is taken from the main OCR records (635 pages matched). Paired tests per document; only the second-reader threshold is tuned (dev split).

- docres: rss_start 1103.1, rss_ppocr 1162.6, docres_mb 183.3, rss_model 1633.4
- unionst: rss_start 1090.4, rss_ppocr 1148.2, unionst_missing_keys 0, unionst_mb 97.6, rss_model 1711.1
- unirec: rss_start 1084.0, rss_ppocr 1141.5, unirec_mb 719.1, rss_model 1990.9

### Same crops: CER / WER / numeric-token exact

| slice | chars | v6s | v6m | unionst_line | unionst_words | unirec subset: v6s | v6m | unirec |
|---|---|---|---|---|---|---|---|---|
| all | 1057503 | 0.117 / 0.168 / 0.895 | 0.226 / 0.274 / 0.887 | 0.678 / 0.935 / 0.459 | 0.300 / 0.485 / 0.763 | 0.229 / 0.288 / 0.890 | 0.368 / 0.409 / 0.879 | 0.370 / 0.299 / 0.802 |
| funsd | 44883 | 0.068 / 0.277 / 0.455 | 0.070 / 0.272 / 0.462 | 0.414 / 0.924 / 0.161 | 0.223 / 0.622 / 0.336 | 0.074 / 0.275 / 0.461 | 0.073 / 0.276 / 0.469 | 0.108 / 0.333 / 0.416 |
| sroie | 98147 | 0.264 / 0.403 / 0.867 | 0.262 / 0.388 / 0.891 | 0.399 / 0.835 / 0.424 | 0.294 / 0.544 / 0.777 | 0.272 / 0.407 / 0.878 | 0.271 / 0.397 / 0.893 | 0.474 / 0.514 / 0.753 |
| synth | 914473 | 0.104 / 0.129 / 0.971 | 0.230 / 0.256 / 0.949 | 0.720 / 0.950 / 0.521 | 0.304 / 0.469 / 0.812 | 0.234 / 0.269 / 0.956 | 0.405 / 0.424 / 0.933 | 0.373 / 0.258 / 0.885 |
| synth:lowdpi | 557037 | 0.021 / 0.039 / 0.985 | 0.115 / 0.144 / 0.965 | 0.752 / 0.959 / 0.507 | 0.176 / 0.350 / 0.838 | - | - | - |
| synth:curved | 357436 | 0.234 / 0.269 / 0.956 | 0.405 / 0.424 / 0.933 | 0.671 / 0.936 / 0.535 | 0.504 / 0.652 / 0.786 | 0.234 / 0.269 / 0.956 | 0.405 / 0.424 / 0.933 | 0.373 / 0.258 / 0.885 |

Paired per-document CER vs PP-OCRv6 small and medium (wins = challenger lower CER):

| slice | challenger | baseline | docs | wins | losses | p | mean CER reduction 95% CI |
|---|---|---|---|---|---|---|---|
| all | unionst_line | v6s | 453 | 1 | 452 | 3.9e-134 | [-0.2807, -0.2353] |
| all | unionst_line | v6m | 437 | 1 | 436 | 2.5e-129 | [-0.2465, -0.2076] |
| all | unionst_words | v6s | 453 | 12 | 415 | 3.9e-106 | [-0.0859, -0.0637] |
| all | unionst_words | v6m | 437 | 15 | 394 | 1.4e-96 | [-0.0577, -0.0444] |
| all | unirec | v6s | 347 | 61 | 241 | 1.8e-26 | [-0.2397, -0.0643] |
| all | unirec | v6m | 319 | 76 | 211 | 7.4e-16 | [-0.1742, -0.0018] |
| funsd | unionst_line | v6s | 50 | 1 | 49 | 9.1e-14 | [-0.3745, -0.2817] |
| funsd | unionst_line | v6m | 50 | 1 | 49 | 9.1e-14 | [-0.3716, -0.2844] |
| funsd | unionst_words | v6s | 50 | 1 | 49 | 9.1e-14 | [-0.1816, -0.1107] |
| funsd | unionst_words | v6m | 50 | 1 | 49 | 9.1e-14 | [-0.1777, -0.1172] |
| funsd | unirec | v6s | 25 | 1 | 23 | 3.0e-06 | [-0.0452, -0.0231] |
| funsd | unirec | v6m | 25 | 4 | 21 | 9.1e-04 | [-0.0626, -0.0164] |
| sroie | unionst_line | v6s | 163 | 0 | 163 | 1.7e-49 | [-0.1406, -0.1258] |
| sroie | unionst_line | v6m | 163 | 0 | 163 | 1.7e-49 | [-0.1429, -0.1281] |
| sroie | unionst_words | v6s | 163 | 11 | 149 | 4.6e-32 | [-0.0353, -0.0252] |
| sroie | unionst_words | v6m | 163 | 8 | 153 | 6.8e-36 | [-0.0377, -0.0275] |
| sroie | unirec | v6s | 82 | 2 | 79 | 2.7e-21 | [-0.5393, -0.0358] |
| sroie | unirec | v6m | 82 | 2 | 79 | 2.7e-21 | [-0.5410, -0.0367] |
| synth | unionst_line | v6s | 240 | 0 | 240 | 1.1e-72 | [-0.3679, -0.2890] |
| synth | unionst_line | v6m | 224 | 0 | 224 | 7.4e-68 | [-0.3053, -0.2370] |
| synth | unionst_words | v6s | 240 | 0 | 217 | 9.5e-66 | [-0.1077, -0.0707] |
| synth | unionst_words | v6m | 224 | 6 | 192 | 4.0e-49 | [-0.0517, -0.0350] |
| synth | unirec | v6s | 240 | 58 | 139 | 7.4e-09 | [-0.2137, -0.0424] |
| synth | unirec | v6m | 212 | 70 | 111 | 0.003 | [-0.1116, +0.0501] |

### UnionST on long lines (word-level model, max 25 characters, input squeezed to at most 128 x 32)

| GT line length (chars) | crops | v6s CER | UnionST whole line CER | UnionST word-split CER |
|---|---|---|---|---|
| 1-10 | 11949 | 0.088 | 0.121 | 0.124 |
| 11-25 | 8223 | 0.097 | 0.189 | 0.127 |
| 26-50 | 4910 | 0.081 | 0.384 | 0.123 |
| 51-100 | 2987 | 0.070 | 0.825 | 0.268 |
| 101-+ | 3127 | 0.164 | 0.949 | 0.460 |

### UnionST as a second reader on low-confidence PP-OCRv6 small lines

Threshold from the dev split: re-read the lowest 10% confidence lines (conf <= 0.973); on the test split 9.5% of lines were re-read. Merge: word alignment by edit distance; a token with digits is only changed when both readers agree.

| test split | CER | WER | numeric exact | docs better / worse | p | CI |
|---|---|---|---|---|---|---|
| PP-OCRv6 small | 0.1115 | 0.1618 | 0.8900 | - | - | - |
| + UnionST second reader | 0.1117 | 0.1621 | 0.8900 | 33 / 51 | 0.063 | [-0.0007, -0.0000] |

### DocRes as gated cleanup (page CER end to end, PP-OCRv6 small det+rec)

| case | pages | CER without | CER with DocRes | pages better / worse | median DocRes s/page |
|---|---|---|---|---|---|
| gate: appearance on funsd:real_scan | 10 | 0.0736 | 0.0733 | 5 / 5 | 144.5 |
| gate: appearance on sroie:receipt | 10 | 0.2680 | 0.2649 | 5 / 2 | 177.7 |
| gate: appearance on synth:curved | 6 | 0.6165 | 0.6255 | 2 / 1 | 425.0 |
| gate: appearance on synth:lowdpi | 6 | 0.0043 | 0.0045 | 0 / 1 | 141.0 |
| gate: deshadowing on funsd:real_scan | 2 | 0.1167 | 0.1184 | 0 / 1 | 141.9 |
| gate: deshadowing on sroie:receipt | 2 | 0.2205 | 0.2177 | 1 / 1 | 295.9 |

Gate firing rate by page type: curved 164/240, lowdpi 155/240, real_scan 28/50, receipt 95/163

### CPU time on the same crops (ms per line crop, 4 threads, shared runner)

v6s: 24.4, unionst_line: 64.8, unionst_words: 172.7, unirec: 356.5

**Verdict, extra challengers:**
- **UnionST-SP (word-level scene model):** not usable as a line recognizer.
  - Whole lines: CER 0.678 vs 0.117 for v6s; it loses on 452 of 453 documents. Lines over 25 characters collapse (CER 0.38-0.95), as its config implies.
  - Word-split crops: much better (0.300) but still clearly worse than v6s and v6m (12 wins / 415 losses vs v6s, p = 4e-106).
  - As a second reader on the lowest-confidence 10% of lines (digit tokens change only if both readers agree): no gain. CER 0.1117 vs 0.1115, numeric exact unchanged at 0.890, 33 better / 51 worse documents, p = 0.063.
  - Reject.
- **UniRec-0.1B fp32 (text crops):** worse than both PP-OCRv6 sizes.
  - CER 0.370 vs v6s 0.229 and v6m 0.368 on its own crops; 61 wins / 241 losses vs v6s, p = 2e-26. Receipts are much worse (0.474 vs 0.272).
  - It is 15x slower than v6s and 719 MB. Reject.
- **DocRes, gated:** no measurable benefit on the pages where the gate fired.
  - Receipts: 0.268 to 0.265. FUNSD: 0.074 to 0.073. Curved: 0.617 to 0.626, worse.
  - 141-425 s per page on CPU. Reject.
  - The gate fires on many normal pages (lowdpi 155 of 240, curved 164 of 240), so as configured it would mostly cost time.
- **PP-OCRv6 small stays the best line recognizer** on these crops: CER 0.117, WER 0.168, numeric exact 0.895. Medium on the same crops: 0.226 / 0.274 / 0.887. The full medium-vs-small comparison comes from the main OCR test.

## Gap 1. OCR (status)

**Main test:**
- **Run 44898133792:** scored 2,307 of 2,771 pages and 1,992 of 3,934 OmniDocBench regions with every arm (0 page errors) before its jobs hit their time limits.
- **Run 45140135889** (`ocr-complete-r4.yml`) scores the rest, split by arm group. The full tables are added from its report.
- **Measured cost:** in the main run, Tesseract best per crop averaged 124 s per page, PP-OCRv6 medium det + rec end to end 112 s, whole-page Tesseract best 111 s, and PP-OCRv6 medium rec 82 s. PP-OCRv6 small rec took 2.7 s.

**Timing job** (one thread, own process, Intel Xeon 6975P-C):

| component | items | mean ms | p50 ms | p95 ms |
|---|---|---|---|---|
| det_s | 24 | 1531.5 | 1226.0 | 2616.8 |
| det_m | 24 | 18482.0 | 14510.6 | 33042.7 |
| uvdoc | 8 | 272.4 | 248.5 | 300.5 |
| v6s | 600 | 12.8 | 8.2 | 37.0 |
| v6m | 600 | 733.8 | 486.0 | 2118.9 |
| v5en | 600 | 15.1 | 7.7 | 51.6 |
| crnn | 600 | 2.3 | 1.5 | 5.8 |
| viptr | 600 | 16.2 | 11.5 | 37.4 |
| tess_fast | 600 | 6.9 | 4.7 | 18.4 |
| tess_best | 600 | 12.7 | 8.6 | 34.9 |

- PP-OCRv6 medium is far slower than small: about 57x per line crop (734 vs 12.8 ms), and 12x for the detector per page (18.5 vs 1.5 s).
- The peak-RSS field of this job is the same for every component (it is dominated by the shared crop set), so RAM per model is reported from the extra-challengers run.
