# Round 4 media tests (repo 2, media/)

Status, 2026-11-21: this file holds the parts that have finished.
- Gap 1 is complete, including the stratified extra-challenger rerun (45152123157).
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

**Run:** 45152123157 (`ocr-extra-r4.yml`), stratified sample.
- Synthetic: every 4th base document (every 8th for UniRec) with all 8 degradations. FUNSD and SROIE pages sampled by id hash.
- 14 of 15 jobs succeeded.
- **Missing DocRes shard:** `extra (docres, 2, 6)` hit the 170-minute limit and was not rerun; DocRes is rejected regardless.
  - So the DocRes table covers 5 of 6 shards: 590 gate-checked pages, 64 DocRes runs.
  - Gate-firing rates are over those pages.

**Per-item files checked (good jobs):**
- 708 pages, 33,065 line crops, 0 errors.
- UnionST: 708 pages with every arm (v6s, whole line, word-split, second-reader merge). UniRec: 346 pages.
- Crop counts identical between jobs.
- PP-OCRv6 medium on the same crops was taken from the merged main OCR records (708 of 708 pages matched; re-aggregated with the completed main run).

**Models and resources:**
- UnionST-SP: 97.6 MB, MIT card, no LICENSE file; OpenOCR code Apache-2.0. Process RSS 1.61 GB.
- UniRec-0.1B: ONNX fp32, 719 MB, Apache card. RSS 2.04 GB.
- DocRes: 183 MB, MIT; tiled float32 on CPU. RSS 1.61 GB.
- CPU per line crop (4 threads): v6s 30 ms, UnionST line 70 ms, UnionST word-split 224 ms, UniRec 411 ms. DocRes 90-484 s per page.

Same pages and the same PP-OCRv6 small detector crops as the main OCR test (UnionST and DocRes: every 4th page; UniRec: every 8th page). Pages with records: 708, line crops: 33065, page errors 0, crop-count mismatches between jobs 0. PP-OCRv6 medium on the same crops is taken from the main OCR records (708 pages matched). Paired tests per document; only the second-reader threshold is tuned (dev split).

- docres: rss_start 1077.2, rss_ppocr 1138.2, docres_mb 183.3, rss_model 1608.7
- unionst: rss_start 1088.8, rss_ppocr 1148.4, unionst_missing_keys 0, unionst_mb 97.6, rss_model 1614.6
- unirec: rss_start 1087.5, rss_ppocr 1148.5, unirec_mb 719.1, rss_model 2038.4

### Same crops: CER / WER / numeric-token exact

| slice | chars | v6s | v6m | unionst_line | unionst_words | unirec subset: v6s | v6m | unirec |
|---|---|---|---|---|---|---|---|---|
| all | 1209049 | 0.110 / 0.156 / 0.893 | 0.154 / 0.206 / 0.899 | 0.726 / 0.940 / 0.460 | 0.267 / 0.484 / 0.768 | 0.112 / 0.157 / 0.892 | 0.143 / 0.190 / 0.899 | 0.141 / 0.194 / 0.813 |
| funsd | 48372 | 0.049 / 0.224 / 0.537 | 0.057 / 0.222 / 0.540 | 0.456 / 0.916 / 0.226 | 0.217 / 0.585 / 0.410 | 0.047 / 0.220 / 0.536 | 0.046 / 0.210 / 0.537 | 0.129 / 0.275 / 0.517 |
| sroie | 107263 | 0.254 / 0.390 / 0.872 | 0.251 / 0.372 / 0.896 | 0.388 / 0.828 / 0.433 | 0.282 / 0.522 / 0.795 | 0.248 / 0.382 / 0.874 | 0.245 / 0.363 / 0.896 | 0.333 / 0.460 / 0.751 |
| synth | 1053414 | 0.098 / 0.121 / 0.958 | 0.148 / 0.183 / 0.951 | 0.773 / 0.956 / 0.511 | 0.268 / 0.473 / 0.800 | 0.103 / 0.127 / 0.950 | 0.138 / 0.168 / 0.948 | 0.125 / 0.159 / 0.888 |
| synth:clean | 138201 | 0.000 / 0.002 / 0.988 | 0.000 / 0.002 / 0.991 | 0.762 / 0.958 / 0.507 | 0.020 / 0.119 / 0.894 | 0.000 / 0.002 / 0.987 | 0.000 / 0.002 / 0.990 | 0.010 / 0.057 / 0.931 |
| synth:lowdpi | 138198 | 0.001 / 0.006 / 0.986 | 0.070 / 0.101 / 0.967 | 0.772 / 0.958 / 0.509 | 0.145 / 0.396 / 0.815 | 0.001 / 0.005 / 0.977 | 0.018 / 0.041 / 0.962 | 0.008 / 0.030 / 0.861 |
| synth:blur | 138052 | 0.003 / 0.016 / 0.982 | 0.122 / 0.170 / 0.964 | 0.786 / 0.958 / 0.506 | 0.481 / 0.645 / 0.751 | 0.005 / 0.023 / 0.975 | 0.107 / 0.146 / 0.962 | 0.016 / 0.040 / 0.929 |
| synth:noise | 138200 | 0.004 / 0.036 / 0.978 | 0.001 / 0.009 / 0.989 | 0.763 / 0.958 / 0.507 | 0.153 / 0.671 / 0.688 | 0.005 / 0.041 / 0.977 | 0.001 / 0.010 / 0.985 | 0.011 / 0.064 / 0.913 |
| synth:skew | 138476 | 0.569 / 0.660 / 0.831 | 0.570 / 0.663 / 0.830 | 0.824 / 0.960 / 0.507 | 0.596 / 0.752 / 0.758 | 0.585 / 0.673 / 0.814 | 0.586 / 0.674 / 0.814 | 0.619 / 0.708 / 0.746 |
| synth:curved | 85887 | 0.266 / 0.292 / 0.952 | 0.419 / 0.439 / 0.935 | 0.702 / 0.934 / 0.538 | 0.546 / 0.702 / 0.789 | 0.274 / 0.299 / 0.941 | 0.432 / 0.455 / 0.928 | 0.348 / 0.301 / 0.866 |
| synth:jpeg | 138199 | 0.003 / 0.022 / 0.953 | 0.106 / 0.172 / 0.943 | 0.784 / 0.958 / 0.509 | 0.296 / 0.498 / 0.810 | 0.003 / 0.021 / 0.936 | 0.047 / 0.106 / 0.950 | 0.043 / 0.061 / 0.924 |
| synth:faded | 138201 | 0.000 / 0.001 / 0.992 | 0.000 / 0.002 / 0.987 | 0.762 / 0.958 / 0.507 | 0.010 / 0.089 / 0.895 | 0.000 / 0.002 / 0.990 | 0.000 / 0.002 / 0.988 | 0.010 / 0.051 / 0.936 |

Paired per-document CER vs PP-OCRv6 small and medium (wins = challenger lower CER):

| slice | challenger | baseline | docs | wins | losses | p | mean CER reduction 95% CI |
|---|---|---|---|---|---|---|---|
| all | unionst_line | v6s | 288 | 0 | 288 | 4.0e-87 | [-0.2428, -0.1987] |
| all | unionst_line | v6m | 288 | 0 | 288 | 4.0e-87 | [-0.2385, -0.1966] |
| all | unionst_words | v6s | 288 | 20 | 267 | 2.6e-56 | [-0.0727, -0.0534] |
| all | unionst_words | v6m | 288 | 11 | 273 | 1.3e-66 | [-0.0683, -0.0515] |
| all | unirec | v6s | 136 | 9 | 121 | 3.5e-26 | [-0.1066, -0.0372] |
| all | unirec | v6m | 136 | 15 | 119 | 2.9e-21 | [-0.1058, -0.0359] |
| funsd | unionst_line | v6s | 54 | 0 | 54 | 1.1e-16 | [-0.4101, -0.3230] |
| funsd | unionst_line | v6m | 54 | 0 | 54 | 1.1e-16 | [-0.4055, -0.3147] |
| funsd | unionst_words | v6s | 54 | 0 | 54 | 1.1e-16 | [-0.1844, -0.1232] |
| funsd | unionst_words | v6m | 54 | 0 | 54 | 1.1e-16 | [-0.1766, -0.1189] |
| funsd | unirec | v6s | 24 | 0 | 24 | 1.2e-07 | [-0.1343, -0.0233] |
| funsd | unirec | v6m | 24 | 1 | 23 | 3.0e-06 | [-0.1360, -0.0243] |
| sroie | unionst_line | v6s | 174 | 0 | 174 | 8.4e-53 | [-0.1392, -0.1257] |
| sroie | unionst_line | v6m | 174 | 0 | 174 | 8.4e-53 | [-0.1420, -0.1285] |
| sroie | unionst_words | v6s | 174 | 20 | 153 | 1.5e-26 | [-0.0319, -0.0233] |
| sroie | unionst_words | v6m | 174 | 10 | 160 | 6.0e-36 | [-0.0346, -0.0262] |
| sroie | unirec | v6s | 82 | 5 | 73 | 1.5e-16 | [-0.1393, -0.0354] |
| sroie | unirec | v6m | 82 | 5 | 76 | 2.3e-17 | [-0.1428, -0.0382] |
| synth | unionst_line | v6s | 60 | 0 | 60 | 1.7e-18 | [-0.4267, -0.2643] |
| synth | unionst_line | v6m | 60 | 0 | 60 | 1.7e-18 | [-0.4035, -0.2521] |
| synth | unionst_words | v6s | 60 | 0 | 60 | 1.7e-18 | [-0.1103, -0.0603] |
| synth | unionst_words | v6m | 60 | 1 | 59 | 1.1e-16 | [-0.0840, -0.0504] |
| synth | unirec | v6s | 30 | 4 | 24 | 1.8e-04 | [-0.0741, -0.0106] |
| synth | unirec | v6m | 30 | 9 | 20 | 0.061 | [-0.0641, +0.0068] |

### UnionST on long lines (word-level model, max 25 characters, input squeezed to at most 128 x 32)

| GT line length (chars) | crops | v6s CER | UnionST whole line CER | UnionST word-split CER |
|---|---|---|---|---|
| 1-10 | 12754 | 0.135 | 0.129 | 0.173 |
| 11-25 | 8395 | 0.106 | 0.195 | 0.144 |
| 26-50 | 3963 | 0.127 | 0.364 | 0.171 |
| 51-100 | 3141 | 0.068 | 0.856 | 0.200 |
| 101-+ | 4151 | 0.120 | 0.941 | 0.352 |

### UnionST as a second reader on low-confidence PP-OCRv6 small lines

Threshold from the dev split: re-read the lowest 10% confidence lines (conf <= 0.972); on the test split 8.0% of lines were re-read. Merge: word alignment by edit distance; a token with digits is only changed when both readers agree.

| test split | CER | WER | numeric exact | docs better / worse | p | CI |
|---|---|---|---|---|---|---|
| PP-OCRv6 small | 0.0973 | 0.1387 | 0.9030 | - | - | - |
| + UnionST second reader | 0.0974 | 0.1392 | 0.9030 | 31 / 54 | 0.017 | [-0.0012, -0.0003] |

Second reader per slice (test split, same threshold): CER v6s -> v6s + UnionST re-read

| slice | v6s CER | + second reader CER | docs better / worse |
|---|---|---|---|
| all | 0.0973 | 0.0974 | 31 / 54 |
| funsd | 0.0448 | 0.0476 | 7 / 10 |
| sroie | 0.2469 | 0.2472 | 22 / 38 |
| synth | 0.0843 | 0.0844 | 2 / 6 |
| synth:clean | 0.0001 | 0.0001 | 0 / 2 |
| synth:lowdpi | 0.0007 | 0.0008 | 0 / 2 |
| synth:blur | 0.0026 | 0.0027 | 0 / 3 |
| synth:noise | 0.0031 | 0.0030 | 2 / 2 |
| synth:skew | 0.4724 | 0.4725 | 0 / 5 |
| synth:curved | 0.2532 | 0.2531 | 1 / 4 |
| synth:jpeg | 0.0027 | 0.0028 | 0 / 2 |
| synth:faded | 0.0000 | 0.0001 | 0 / 1 |

### DocRes as gated cleanup (page CER end to end, PP-OCRv6 small det+rec)

| case | pages | CER without | CER with DocRes | pages better / worse | median DocRes s/page |
|---|---|---|---|---|---|
| forced on clean pages (gate did not fire) | 4 | 0.0000 | 0.0061 | 0 / 1 | 483.7 |
| gate: appearance on funsd:real_scan | 9 | 0.0495 | 0.0497 | 5 / 3 | 91.2 |
| gate: appearance on sroie:receipt | 9 | 0.2447 | 0.2434 | 2 / 6 | 181.7 |
| gate: appearance on synth:clean | 4 | 0.0004 | 0.0004 | 0 / 0 | 307.5 |
| gate: appearance on synth:curved | 6 | 0.6631 | 0.6589 | 3 / 2 | 303.0 |
| gate: appearance on synth:faded | 4 | 0.0003 | 0.0003 | 0 / 0 | 301.3 |
| gate: appearance on synth:jpeg | 4 | 0.0043 | 0.0032 | 1 / 0 | 190.0 |
| gate: appearance on synth:lowdpi | 6 | 0.0043 | 0.0045 | 0 / 1 | 90.4 |
| gate: appearance on synth:noise | 6 | 0.0063 | 0.0073 | 0 / 2 | 293.7 |
| gate: appearance on synth:skew | 4 | 0.5535 | 0.5614 | 0 / 3 | 469.7 |
| gate: deblurring on synth:blur | 4 | 0.0005 | 0.0014 | 0 / 1 | 467.4 |
| gate: deblurring on synth:faded | 2 | 0.0000 | 0.0000 | 0 / 0 | 474.2 |
| gate: deshadowing on funsd:real_scan | 1 | 0.0836 | 0.0836 | 0 / 0 | 89.9 |
| gate: deshadowing on sroie:receipt | 1 | 0.2733 | 0.2632 | 1 / 0 | 136.6 |

Gate firing rate by page type: blur 36/60, clean 28/60, curved 42/60, faded 60/60, jpeg 26/60, lowdpi 39/60, noise 39/60, real_scan 23/54, receipt 81/174, skew 28/60

### CPU time on the same crops (ms per line crop, 4 threads, shared runner)

v6s: 30.1, unionst_line: 69.9, unionst_words: 223.7, unirec: 410.5

**Verdict, extra challengers** (unchanged from the preliminary run; now holds on all 8 defect types):
- **UnionST-SP: reject.**
  - Whole lines: CER 0.726 vs 0.110; 0 wins on 288 documents.
  - Word-split: 0.267, worse on every defect type (e.g. blur 0.481 vs 0.003; JPEG 0.296 vs 0.003).
  - Second reader on the lowest-confidence 8-10% of lines: CER 0.0974 vs 0.0973, 31 better / 54 worse (p = 0.017, against it). Numeric exact unchanged (0.903).
- **UniRec-0.1B fp32: reject.**
  - On its own crops: 0.141 vs v6s 0.112 (9 / 121 documents, p = 4e-26). Better than v6m on blur, JPEG and curved, but never better than v6s.
  - 14x slower and 719 MB.
- **DocRes, gated: reject.**
  - No reliable gain: deblurring made blur pages worse (0.0005 to 0.0014); appearance changes were within ±0.01; on wrongly gated clean pages it added errors (0 to 0.006).
  - The gate fires on most pages (faded 60 of 60, curved 42 of 60, even clean 28 of 60).
  - 1.5-8 minutes per page on CPU.
- **PP-OCRv6 small stays the pick.**

## Gap 1. OCR on scanned English documents

**Runs:**
- 44898133792 (all arms; 2,307 pages and 1,992 regions before its jobs timed out).
- 45140135889 (`ocr-complete-r4.yml`, the missing 464 pages and 1,942 regions, split by arm group).
- Merged by id: **2,771 / 2,771 pages and 3,934 / 3,934 regions, every crop arm on every page, 0 errors, 0 crop-count mismatches** between jobs.
- Speed: timing job below. Memory: a Python process with PP-OCRv6 small loaded uses about 1.15 GB RSS, of which about 60 MB is the model; RSS for the other models is in "OCR: extra challengers".

**PP-OCRv6 medium setup check (done before trusting small > medium):**
- **Preprocessing matches docling.rs `ocr_prep.rs`:**
  - height 48, width round(48 w/h) with no practical cap, bilinear resize;
  - RGB planes, (x/127.5 - 1);
  - greedy CTC with index 0 = blank, then the dictionary lines, then a trailing space class;
  - no padding (docling batches equal widths only).
- **Same dictionary as small:** the medium dictionary from the RapidOCR hub is byte-identical to docling.rs's `ocr_rec_v6_dict.txt` (sha256 b5f2bfe2…). The class-count check passed. docling.rs ships only the small model; medium uses identical pre/post-processing here.
- **Where medium loses:** only on long synthetic lines. By crop width at height 48:
  - up to 320 px: synthetic CER 0.006 vs 0.007, the same;
  - 640-1280 px: 0.158 vs 0.336;
  - FUNSD and SROIE: equal or better for medium at every width.
- **Diagnostic run 45153361907** (report / tiny-print templates, lowdpi and curved; 899 crops): on many 100+ character lines medium emits a few characters or nothing ("Bd de e", "A dee") while small reads them correctly. BGR input, PIL resizing and cutting lines into pieces of at most 640 px do not fix it (cutting recovers only part).
- **Official Paddle Inference, run 45166281484:** paddlepaddle 3.3.1 with the RapidOCR-hub Paddle files, PaddleX OCRReisizeNormImg preprocessing (BGR, padding to at least 320 px, cap 3200), 209 crops of 40+ characters.
  - medium: ONNX 0.514 vs Paddle 0.516;
  - small: ONNX 0.101 vs Paddle 0.100;
  - the ONNX model fed the Paddle preprocessing reproduces Paddle's strings exactly.
- **Conclusion: no setup bug.** The collapse on long, dense printed lines is the PP-OCRv6 medium model's own behaviour, identical in Paddle and ONNX, so the medium numbers below stand unchanged.
- **Caveats on the data:**
  - Medium wins more documents than small overall (303 vs 198, p = 3e-6) but has a higher micro-averaged CER (0.155 vs 0.111), because its failures are catastrophic whole-line drops.
  - On receipts and noisy pages medium is slightly better.

Pages: 2771 (errors 0); OmniDocBench regions: 3934. Baseline `v6s` = docling.rs models-v1 `ocr_det.onnx` + `ocr_rec_v6.onnx` (PP-OCRv6 **small**, per the release manifest), with docling.rs pre/post-processing ported to Python. CER/WER are micro-averaged; paired tests are per document (sign test on per-document CER, bootstrap 95% CI of the mean CER reduction), on the held-out test split.

### 1a. Same detector crops (PP-OCRv6 small boxes), test split: CER / WER / numeric-token exact

| slice | crops chars | v6s | v6m | v5en | crnn | viptr | tess_fast | tess_best |
|---|---|---|---|---|---|---|---|---|
| all | 2395286 | 0.111 / 0.160 / 0.897 | 0.155 / 0.202 / 0.901 | 0.171 / 0.217 / 0.888 | 0.267 / 0.939 / 0.471 | 0.247 / 0.939 / 0.470 | 0.126 / 0.219 / 0.791 | 0.125 / 0.201 / 0.819 |
| funsd | 93777 | 0.050 / 0.232 / 0.491 | 0.058 / 0.238 / 0.493 | 0.064 / 0.258 / 0.474 | 0.213 / 0.907 / 0.224 | 0.193 / 0.907 / 0.224 | 0.094 / 0.327 / 0.379 | 0.087 / 0.301 / 0.404 |
| sroie | 217942 | 0.259 / 0.392 / 0.870 | 0.258 / 0.378 / 0.891 | 0.268 / 0.399 / 0.868 | 0.389 / 0.832 / 0.427 | 0.379 / 0.832 / 0.424 | 0.300 / 0.509 / 0.660 | 0.298 / 0.498 / 0.706 |
| synth | 2083567 | 0.098 / 0.124 / 0.969 | 0.148 / 0.176 / 0.963 | 0.166 / 0.190 / 0.956 | 0.256 / 0.955 / 0.534 | 0.236 / 0.955 / 0.534 | 0.110 / 0.173 / 0.935 | 0.109 / 0.155 / 0.952 |
| synth:clean | 272882 | 0.000 / 0.001 / 0.998 | 0.000 / 0.001 / 0.999 | 0.000 / 0.001 / 0.999 | 0.132 / 0.956 / 0.532 | 0.126 / 0.956 / 0.531 | 0.000 / 0.002 / 0.991 | 0.000 / 0.001 / 0.994 |
| synth:lowdpi | 272870 | 0.022 / 0.038 / 0.989 | 0.110 / 0.132 / 0.969 | 0.119 / 0.134 / 0.963 | 0.207 / 0.957 / 0.531 | 0.191 / 0.957 / 0.531 | 0.022 / 0.078 / 0.947 | 0.027 / 0.072 / 0.963 |
| synth:blur | 272805 | 0.015 / 0.034 / 0.989 | 0.135 / 0.164 / 0.973 | 0.182 / 0.201 / 0.959 | 0.282 / 0.957 / 0.530 | 0.209 / 0.957 / 0.530 | 0.104 / 0.198 / 0.915 | 0.097 / 0.162 / 0.920 |
| synth:noise | 272882 | 0.004 / 0.030 / 0.980 | 0.002 / 0.009 / 0.994 | 0.003 / 0.017 / 0.986 | 0.147 / 0.959 / 0.523 | 0.139 / 0.957 / 0.527 | 0.027 / 0.204 / 0.875 | 0.015 / 0.102 / 0.954 |
| synth:skew | 273413 | 0.544 / 0.632 / 0.867 | 0.544 / 0.632 / 0.867 | 0.545 / 0.633 / 0.867 | 0.602 / 0.959 / 0.533 | 0.590 / 0.959 / 0.532 | 0.544 / 0.632 / 0.860 | 0.544 / 0.632 / 0.864 |
| synth:curved | 172951 | 0.214 / 0.242 / 0.972 | 0.369 / 0.383 / 0.947 | 0.395 / 0.404 / 0.947 | 0.388 / 0.932 / 0.561 | 0.356 / 0.932 / 0.561 | 0.194 / 0.207 / 0.966 | 0.194 / 0.208 / 0.970 |
| synth:jpeg | 272882 | 0.027 / 0.059 / 0.962 | 0.107 / 0.162 / 0.959 | 0.166 / 0.203 / 0.936 | 0.210 / 0.957 / 0.529 | 0.195 / 0.957 / 0.530 | 0.018 / 0.072 / 0.942 | 0.024 / 0.077 / 0.952 |
| synth:faded | 272882 | 0.000 / 0.000 / 0.997 | 0.000 / 0.001 / 0.996 | 0.000 / 0.001 / 0.993 | 0.131 / 0.956 / 0.533 | 0.124 / 0.956 / 0.531 | 0.001 / 0.004 / 0.989 | 0.000 / 0.002 / 0.995 |
| synth:tiny_print | 1008070 | 0.138 / 0.186 / 0.847 | 0.234 / 0.287 / 0.794 | 0.267 / 0.312 / 0.753 | 0.338 / 0.998 / 0.000 | 0.304 / 0.998 / 0.000 | 0.158 / 0.258 / 0.772 | 0.158 / 0.237 / 0.794 |

Paired per-document CER vs v6s (test split; wins = documents where the challenger has lower CER):

| slice | challenger | docs | wins | losses | p | mean CER reduction 95% CI |
|---|---|---|---|---|---|---|
| all | v6m | 582 | 303 | 198 | 3.1e-06 | [-0.0056, -0.0012] |
| all | v5en | 582 | 168 | 350 | 9.3e-16 | [-0.0154, -0.0095] |
| all | crnn | 582 | 0 | 582 | 1.3e-175 | [-0.1329, -0.1259] |
| all | viptr | 582 | 0 | 582 | 1.3e-175 | [-0.1214, -0.1157] |
| all | tess_fast | 582 | 13 | 558 | 2.5e-146 | [-0.0365, -0.0303] |
| all | tess_best | 582 | 17 | 554 | 4.3e-140 | [-0.0337, -0.0275] |
| funsd | v6m | 108 | 55 | 40 | 0.151 | [-0.0115, -0.0005] |
| funsd | v5en | 108 | 15 | 82 | 2.4e-12 | [-0.0176, -0.0069] |
| funsd | crnn | 108 | 0 | 108 | 6.2e-33 | [-0.1622, -0.1432] |
| funsd | viptr | 108 | 0 | 108 | 6.2e-33 | [-0.1432, -0.1276] |
| funsd | tess_fast | 108 | 0 | 107 | 1.2e-32 | [-0.0509, -0.0360] |
| funsd | tess_best | 108 | 0 | 106 | 2.5e-32 | [-0.0438, -0.0294] |
| sroie | v6m | 353 | 213 | 107 | 3.2e-09 | [+0.0010, +0.0026] |
| sroie | v5en | 353 | 116 | 205 | 7.7e-07 | [-0.0120, -0.0070] |
| sroie | crnn | 353 | 0 | 353 | 1.1e-106 | [-0.1318, -0.1249] |
| sroie | viptr | 353 | 0 | 353 | 1.1e-106 | [-0.1220, -0.1161] |
| sroie | tess_fast | 353 | 10 | 333 | 6.3e-85 | [-0.0439, -0.0352] |
| sroie | tess_best | 353 | 12 | 335 | 3.8e-83 | [-0.0421, -0.0333] |
| synth | v6m | 121 | 35 | 51 | 0.105 | [-0.0255, -0.0080] |
| synth | v5en | 121 | 37 | 63 | 0.012 | [-0.0337, -0.0112] |
| synth | crnn | 121 | 0 | 121 | 7.5e-37 | [-0.1201, -0.1019] |
| synth | viptr | 121 | 0 | 121 | 7.5e-37 | [-0.1088, -0.0943] |
| synth | tess_fast | 121 | 3 | 118 | 2.2e-31 | [-0.0098, -0.0050] |
| synth | tess_best | 121 | 5 | 113 | 1.1e-27 | [-0.0081, -0.0029] |
| synth:clean | v6m | 121 | 10 | 5 | 0.302 | [-0.0005, +0.0001] |
| synth:clean | v5en | 121 | 13 | 6 | 0.167 | [-0.0004, +0.0002] |
| synth:clean | crnn | 121 | 0 | 121 | 7.5e-37 | [-0.1081, -0.0956] |
| synth:clean | viptr | 121 | 0 | 121 | 7.5e-37 | [-0.1033, -0.0913] |
| synth:clean | tess_fast | 121 | 5 | 33 | 4.3e-06 | [-0.0007, -0.0002] |
| synth:clean | tess_best | 121 | 9 | 21 | 0.043 | [-0.0005, -0.0001] |
| synth:lowdpi | v6m | 121 | 7 | 15 | 0.134 | [-0.0443, -0.0061] |
| synth:lowdpi | v5en | 121 | 12 | 23 | 0.090 | [-0.0489, -0.0072] |
| synth:lowdpi | crnn | 121 | 0 | 121 | 7.5e-37 | [-0.1315, -0.1046] |
| synth:lowdpi | viptr | 121 | 0 | 121 | 7.5e-37 | [-0.1239, -0.1005] |
| synth:lowdpi | tess_fast | 121 | 4 | 83 | 3.0e-20 | [-0.0084, +0.0032] |
| synth:lowdpi | tess_best | 121 | 7 | 74 | 3.2e-15 | [-0.0085, +0.0033] |
| synth:blur | v6m | 121 | 15 | 16 | 1.000 | [-0.0571, -0.0133] |
| synth:blur | v5en | 121 | 9 | 22 | 0.029 | [-0.0783, -0.0192] |
| synth:blur | crnn | 121 | 0 | 121 | 7.5e-37 | [-0.1707, -0.1213] |
| synth:blur | viptr | 121 | 0 | 121 | 7.5e-37 | [-0.1349, -0.1061] |
| synth:blur | tess_fast | 121 | 2 | 71 | 5.7e-19 | [-0.0491, -0.0173] |
| synth:blur | tess_best | 121 | 5 | 58 | 1.7e-12 | [-0.0474, -0.0171] |
| synth:noise | v6m | 121 | 43 | 12 | 3.3e-05 | [+0.0001, +0.0011] |
| synth:noise | v5en | 121 | 41 | 32 | 0.349 | [-0.0008, +0.0005] |
| synth:noise | crnn | 121 | 0 | 121 | 7.5e-37 | [-0.1180, -0.1047] |
| synth:noise | viptr | 121 | 0 | 121 | 7.5e-37 | [-0.1112, -0.0991] |
| synth:noise | tess_fast | 121 | 0 | 121 | 7.5e-37 | [-0.0259, -0.0220] |
| synth:noise | tess_best | 121 | 1 | 119 | 1.8e-34 | [-0.0117, -0.0096] |
| synth:skew | v6m | 121 | 5 | 8 | 0.581 | [-0.0007, -0.0001] |
| synth:skew | v5en | 121 | 15 | 9 | 0.307 | [-0.0010, +0.0003] |
| synth:skew | crnn | 121 | 0 | 121 | 7.5e-37 | [-0.0702, -0.0619] |
| synth:skew | viptr | 121 | 0 | 121 | 7.5e-37 | [-0.0635, -0.0547] |
| synth:skew | tess_fast | 121 | 8 | 18 | 0.076 | [-0.0006, -0.0001] |
| synth:skew | tess_best | 121 | 9 | 24 | 0.014 | [-0.0007, -0.0001] |
| synth:curved | v6m | 121 | 9 | 42 | 3.4e-06 | [-0.1029, -0.0460] |
| synth:curved | v5en | 121 | 12 | 40 | 1.3e-04 | [-0.1185, -0.0554] |
| synth:curved | crnn | 121 | 0 | 121 | 7.5e-37 | [-0.1453, -0.1132] |
| synth:curved | viptr | 121 | 0 | 121 | 7.5e-37 | [-0.1235, -0.1003] |
| synth:curved | tess_fast | 121 | 24 | 36 | 0.155 | [+0.0016, +0.0129] |
| synth:curved | tess_best | 121 | 17 | 40 | 0.003 | [+0.0014, +0.0126] |
| synth:jpeg | v6m | 121 | 32 | 24 | 0.350 | [-0.0388, -0.0073] |
| synth:jpeg | v5en | 121 | 33 | 26 | 0.435 | [-0.0653, -0.0151] |
| synth:jpeg | crnn | 121 | 0 | 121 | 7.5e-37 | [-0.1309, -0.1063] |
| synth:jpeg | viptr | 121 | 0 | 121 | 7.5e-37 | [-0.1227, -0.1011] |
| synth:jpeg | tess_fast | 121 | 26 | 61 | 2.2e-04 | [-0.0029, +0.0078] |
| synth:jpeg | tess_best | 121 | 27 | 50 | 0.012 | [-0.0040, +0.0071] |
| synth:faded | v6m | 121 | 6 | 11 | 0.332 | [-0.0004, -0.0000] |
| synth:faded | v5en | 121 | 13 | 11 | 0.839 | [-0.0004, +0.0001] |
| synth:faded | crnn | 121 | 0 | 121 | 7.5e-37 | [-0.1069, -0.0942] |
| synth:faded | viptr | 121 | 0 | 121 | 7.5e-37 | [-0.1021, -0.0907] |
| synth:faded | tess_fast | 121 | 1 | 48 | 1.8e-13 | [-0.0012, -0.0005] |
| synth:faded | tess_best | 121 | 6 | 30 | 7.0e-05 | [-0.0008, -0.0002] |
| synth:tiny_print | v6m | 19 | 2 | 17 | 7.3e-04 | [-0.1267, -0.0423] |
| synth:tiny_print | v5en | 19 | 0 | 19 | 3.8e-06 | [-0.1648, -0.0611] |
| synth:tiny_print | crnn | 19 | 0 | 19 | 3.8e-06 | [-0.2166, -0.1679] |
| synth:tiny_print | viptr | 19 | 0 | 19 | 3.8e-06 | [-0.1784, -0.1444] |
| synth:tiny_print | tess_fast | 19 | 2 | 17 | 7.3e-04 | [-0.0328, -0.0062] |
| synth:tiny_print | tess_best | 19 | 2 | 17 | 7.3e-04 | [-0.0328, -0.0037] |

### 1b. Tesseract best only on low-confidence lines (threshold picked on the dev split)

| mode | tau (dev) | test CER | v6s test CER | docs | wins | losses | p | CI |
|---|---|---|---|---|---|---|---|---|
| rep | 0.6 | 0.1070 | 0.1107 | 582 | 21 | 46 | 0.003 | [-0.0005, +0.0004] |
| rep_if_higher | 0.98 | 0.1092 | 0.1107 | 582 | 48 | 52 | 0.764 | [-0.0002, +0.0001] |

### 1c. End to end (detector + recognizer), test split

**all** (1429 pages)

| arm | page CER | bag-of-words F1 | numeric recall | numeric precision | critical fields exact | docs | wins | losses | p (CER vs v6s) | extra ms/page |
|---|---|---|---|---|---|---|---|---|---|---|
| v6s | 0.1607 | 0.9081 | 0.8987 | 0.9174 | 0.9731 | 0 | 0 | 0 | - | - |
| v6m | 0.2031 | 0.8811 | 0.9036 | 0.9234 | 0.9757 | 582 | 297 | 201 | 2.0e-05 | - |
| v5en | 0.2174 | 0.8731 | 0.8895 | 0.9151 | 0.9687 | 582 | 187 | 343 | 1.2e-11 | - |
| crnn | 0.3030 | 0.0995 | 0.4675 | 0.5383 | 0.8815 | 582 | 0 | 582 | 1.3e-175 | - |
| viptr | 0.2849 | 0.0999 | 0.4667 | 0.5383 | 0.8808 | 582 | 0 | 582 | 1.3e-175 | - |
| tess_fast | 0.1747 | 0.8548 | 0.7960 | 0.8163 | 0.9123 | 582 | 15 | 556 | 3.8e-143 | - |
| tess_best | 0.1736 | 0.8701 | 0.8233 | 0.8323 | 0.9264 | 582 | 18 | 552 | 2.6e-138 | - |
| v6m_det+rec | 0.1703 | 0.9072 | 0.9089 | 0.9248 | 0.9764 | 582 | 296 | 236 | 0.010 | 108657 |
| tess_fast_page | 0.1850 | 0.8033 | 0.7150 | 0.7677 | 0.7939 | 582 | 42 | 538 | 9.9e-111 | 56886 |
| tess_best_page | 0.1909 | 0.8069 | 0.7325 | 0.7751 | 0.7917 | 582 | 49 | 530 | 5.3e-103 | 93140 |
| hyb_rep_0.6 | 0.1567 | 0.9087 | 0.8990 | 0.9156 | 0.9731 | 582 | 50 | 120 | 8.0e-08 | - |
| hyb_rep_if_higher_0.98 | 0.1590 | 0.9102 | 0.8988 | 0.9168 | 0.9734 | 582 | 67 | 86 | 0.145 | - |
| pre_deskew | 0.1619 | 0.9091 | 0.8987 | 0.9163 | 0.9728 | 582 | 108 | 143 | 0.032 | 58 |
| pre_clahe | 0.1611 | 0.9081 | 0.8983 | 0.9148 | 0.9696 | 582 | 200 | 243 | 0.046 | 59 |
| pre_denoise | 0.1775 | 0.8855 | 0.8793 | 0.8931 | 0.9588 | 582 | 146 | 340 | 7.0e-19 | 4473 |
| pre_uvdoc | 0.2052 | 0.8637 | 0.8865 | 0.9085 | 0.9622 | 582 | 190 | 344 | 2.6e-11 | 651 |
| pre_gated | 0.1611 | 0.9090 | 0.8970 | 0.9144 | 0.9697 | 582 | 145 | 185 | 0.032 | 379 |
| pre_gated_uvdoc | 0.1434 | 0.9115 | 0.8954 | 0.9122 | 0.9680 | 582 | 147 | 183 | 0.054 | 496 |

**funsd** (108 pages)

| arm | page CER | bag-of-words F1 | numeric recall | numeric precision | critical fields exact | docs | wins | losses | p (CER vs v6s) | extra ms/page |
|---|---|---|---|---|---|---|---|---|---|---|
| v6s | 0.0871 | 0.8080 | 0.4925 | 0.6029 | 0.9161 | 0 | 0 | 0 | - | - |
| v6m | 0.0948 | 0.8050 | 0.4949 | 0.6032 | 0.9186 | 108 | 57 | 39 | 0.082 | - |
| v5en | 0.0982 | 0.7856 | 0.4736 | 0.5914 | 0.9037 | 108 | 26 | 77 | 4.9e-07 | - |
| crnn | 0.2379 | 0.1405 | 0.2272 | 0.3374 | 0.8266 | 108 | 0 | 108 | 6.2e-33 | - |
| viptr | 0.2192 | 0.1420 | 0.2252 | 0.3448 | 0.8415 | 108 | 0 | 108 | 6.2e-33 | - |
| tess_fast | 0.1276 | 0.7193 | 0.3866 | 0.5070 | 0.8036 | 108 | 2 | 105 | 7.1e-29 | - |
| tess_best | 0.1208 | 0.7441 | 0.4087 | 0.5078 | 0.8104 | 108 | 2 | 104 | 1.4e-28 | - |
| v6m_det+rec | 0.0802 | 0.8137 | 0.5035 | 0.6152 | 0.9195 | 108 | 67 | 34 | 0.001 | 66498 |
| tess_fast_page | 0.2513 | 0.5945 | 0.2787 | 0.4157 | 0.6336 | 108 | 1 | 107 | 6.7e-31 | 36202 |
| tess_best_page | 0.2556 | 0.5950 | 0.2780 | 0.4053 | 0.6161 | 108 | 2 | 106 | 3.6e-29 | 58901 |
| hyb_rep_0.6 | 0.0886 | 0.8055 | 0.4929 | 0.6005 | 0.9161 | 108 | 11 | 37 | 2.2e-04 | - |
| hyb_rep_if_higher_0.98 | 0.0874 | 0.8075 | 0.4929 | 0.6034 | 0.9161 | 108 | 10 | 21 | 0.071 | - |
| pre_deskew | 0.0889 | 0.8066 | 0.4909 | 0.5992 | 0.9152 | 108 | 20 | 17 | 0.743 | 17 |
| pre_clahe | 0.0873 | 0.8073 | 0.4921 | 0.6030 | 0.9178 | 108 | 31 | 30 | 1.000 | 85 |
| pre_denoise | 0.0856 | 0.8085 | 0.4921 | 0.6053 | 0.9144 | 108 | 36 | 43 | 0.500 | 1239 |
| pre_uvdoc | 0.1086 | 0.7993 | 0.4724 | 0.5885 | 0.9024 | 108 | 35 | 64 | 0.005 | 586 |
| pre_gated | 0.0892 | 0.8080 | 0.4929 | 0.6022 | 0.9169 | 108 | 24 | 14 | 0.143 | 11 |
| pre_gated_uvdoc | 0.0909 | 0.8074 | 0.4913 | 0.6032 | 0.9139 | 108 | 19 | 17 | 0.868 | 89 |

**sroie** (353 pages)

| arm | page CER | bag-of-words F1 | numeric recall | numeric precision | critical fields exact | docs | wins | losses | p (CER vs v6s) | extra ms/page |
|---|---|---|---|---|---|---|---|---|---|---|
| v6s | 0.2535 | 0.6200 | 0.8591 | 0.8664 | 0.9722 | 0 | 0 | 0 | - | - |
| v6m | 0.2512 | 0.6330 | 0.8810 | 0.8837 | 0.9742 | 353 | 206 | 112 | 1.5e-07 | - |
| v5en | 0.2625 | 0.6131 | 0.8577 | 0.8702 | 0.9663 | 353 | 122 | 204 | 6.5e-06 | - |
| crnn | 0.3737 | 0.2298 | 0.4230 | 0.5052 | 0.8909 | 353 | 0 | 353 | 1.1e-106 | - |
| viptr | 0.3645 | 0.2297 | 0.4206 | 0.5071 | 0.9236 | 353 | 0 | 353 | 1.1e-106 | - |
| tess_fast | 0.2925 | 0.5156 | 0.6559 | 0.6702 | 0.8284 | 353 | 9 | 334 | 1.9e-86 | - |
| tess_best | 0.2899 | 0.5250 | 0.7005 | 0.7025 | 0.8343 | 353 | 11 | 335 | 2.6e-84 | - |
| v6m_det+rec | 0.2506 | 0.6330 | 0.8836 | 0.8805 | 0.9712 | 353 | 197 | 130 | 2.5e-04 | 61412 |
| tess_fast_page | 0.3724 | 0.4744 | 0.5897 | 0.6536 | 0.7173 | 353 | 9 | 342 | 9.0e-89 | 49583 |
| tess_best_page | 0.3669 | 0.4873 | 0.6280 | 0.6852 | 0.7421 | 353 | 14 | 336 | 3.3e-81 | 77081 |
| hyb_rep_0.6 | 0.2555 | 0.6183 | 0.8591 | 0.8641 | 0.9722 | 353 | 29 | 83 | 3.3e-07 | - |
| hyb_rep_if_higher_0.98 | 0.2542 | 0.6189 | 0.8585 | 0.8643 | 0.9722 | 353 | 34 | 63 | 0.004 | - |
| pre_deskew | 0.2529 | 0.6200 | 0.8595 | 0.8649 | 0.9712 | 353 | 50 | 43 | 0.534 | 95 |
| pre_clahe | 0.2533 | 0.6191 | 0.8634 | 0.8663 | 0.9702 | 353 | 145 | 145 | 1.000 | 87 |
| pre_denoise | 0.2610 | 0.6023 | 0.8315 | 0.8225 | 0.9494 | 353 | 95 | 205 | 2.0e-10 | 7861 |
| pre_uvdoc | 0.2585 | 0.6172 | 0.8604 | 0.8677 | 0.9692 | 353 | 134 | 180 | 0.011 | 667 |
| pre_gated | 0.2533 | 0.6187 | 0.8592 | 0.8653 | 0.9702 | 353 | 84 | 87 | 0.879 | 111 |
| pre_gated_uvdoc | 0.2536 | 0.6191 | 0.8607 | 0.8661 | 0.9702 | 353 | 87 | 86 | 1.000 | 150 |

**synth** (968 pages)

| arm | page CER | bag-of-words F1 | numeric recall | numeric precision | critical fields exact | docs | wins | losses | p (CER vs v6s) | extra ms/page |
|---|---|---|---|---|---|---|---|---|---|---|
| v6s | 0.1541 | 0.9517 | 0.9804 | 0.9870 | 0.9871 | 0 | 0 | 0 | - | - |
| v6m | 0.2028 | 0.9190 | 0.9742 | 0.9865 | 0.9898 | 121 | 34 | 50 | 0.101 | - |
| v5en | 0.2180 | 0.9139 | 0.9673 | 0.9812 | 0.9849 | 121 | 39 | 62 | 0.028 | - |
| crnn | 0.2983 | 0.0753 | 0.5302 | 0.5789 | 0.8940 | 121 | 0 | 121 | 7.5e-37 | - |
| viptr | 0.2794 | 0.0757 | 0.5307 | 0.5759 | 0.8859 | 121 | 0 | 121 | 7.5e-37 | - |
| tess_fast | 0.1642 | 0.9082 | 0.9467 | 0.9451 | 0.9477 | 121 | 4 | 117 | 6.6e-30 | - |
| tess_best | 0.1636 | 0.9236 | 0.9628 | 0.9546 | 0.9645 | 121 | 5 | 113 | 1.1e-27 | - |
| v6m_det+rec | 0.1657 | 0.9490 | 0.9808 | 0.9900 | 0.9908 | 121 | 32 | 72 | 1.1e-04 | 130589 |
| tess_fast_page | 0.1621 | 0.8579 | 0.8591 | 0.8711 | 0.8411 | 121 | 32 | 89 | 2.1e-07 | 61857 |
| tess_best_page | 0.1693 | 0.8602 | 0.8650 | 0.8654 | 0.8398 | 121 | 33 | 88 | 5.9e-07 | 102817 |
| hyb_rep_0.6 | 0.1492 | 0.9527 | 0.9810 | 0.9856 | 0.9871 | 121 | 10 | 0 | 0.002 | - |
| hyb_rep_if_higher_0.98 | 0.1520 | 0.9544 | 0.9811 | 0.9873 | 0.9875 | 121 | 23 | 2 | 1.9e-05 | - |
| pre_deskew | 0.1554 | 0.9529 | 0.9805 | 0.9865 | 0.9871 | 121 | 38 | 83 | 5.3e-05 | 49 |
| pre_clahe | 0.1546 | 0.9519 | 0.9769 | 0.9824 | 0.9822 | 121 | 24 | 68 | 4.9e-06 | 47 |
| pre_denoise | 0.1727 | 0.9277 | 0.9642 | 0.9740 | 0.9706 | 121 | 15 | 92 | 1.1e-14 | 3598 |
| pre_uvdoc | 0.2038 | 0.9005 | 0.9602 | 0.9714 | 0.9760 | 121 | 21 | 100 | 1.6e-13 | 652 |
| pre_gated | 0.1545 | 0.9529 | 0.9772 | 0.9824 | 0.9826 | 121 | 37 | 84 | 2.3e-05 | 518 |
| pre_gated_uvdoc | 0.1341 | 0.9554 | 0.9736 | 0.9776 | 0.9810 | 121 | 41 | 80 | 5.0e-04 | 668 |

**synth:clean** (121 pages)

| arm | page CER | bag-of-words F1 | numeric recall | numeric precision | critical fields exact | docs | wins | losses | p (CER vs v6s) | extra ms/page |
|---|---|---|---|---|---|---|---|---|---|---|
| v6s | 0.0138 | 0.9993 | 0.9979 | 0.9970 | 0.9958 | 0 | 0 | 0 | - | - |
| v6m | 0.0138 | 0.9992 | 0.9987 | 0.9987 | 0.9975 | 121 | 10 | 5 | 0.302 | - |
| v5en | 0.0142 | 0.9988 | 0.9991 | 0.9983 | 0.9983 | 121 | 13 | 6 | 0.167 | - |
| crnn | 0.1417 | 0.0760 | 0.5321 | 0.5681 | 0.9492 | 121 | 0 | 121 | 7.5e-37 | - |
| viptr | 0.1357 | 0.0759 | 0.5313 | 0.5677 | 0.9208 | 121 | 0 | 121 | 7.5e-37 | - |
| tess_fast | 0.0140 | 0.9978 | 0.9915 | 0.9873 | 0.9850 | 121 | 5 | 33 | 4.3e-06 | - |
| tess_best | 0.0139 | 0.9989 | 0.9945 | 0.9928 | 0.9925 | 121 | 10 | 21 | 0.071 | - |
| v6m_det+rec | 0.0175 | 0.9992 | 0.9987 | 0.9987 | 0.9975 | 121 | 15 | 10 | 0.424 | 127254 |
| tess_fast_page | 0.0025 | 0.9943 | 0.9379 | 0.9335 | 0.8925 | 121 | 16 | 36 | 0.008 | 71566 |
| tess_best_page | 0.0026 | 0.9936 | 0.9430 | 0.9434 | 0.9033 | 121 | 15 | 35 | 0.007 | 129750 |
| hyb_rep_0.6 | 0.0138 | 0.9993 | 0.9979 | 0.9970 | 0.9958 | 121 | 0 | 0 | 1.000 | - |
| hyb_rep_if_higher_0.98 | 0.0138 | 0.9993 | 0.9979 | 0.9970 | 0.9958 | 121 | 1 | 0 | 1.000 | - |
| pre_deskew | 0.0138 | 0.9993 | 0.9979 | 0.9970 | 0.9958 | 121 | 0 | 0 | 1.000 | 60 |
| pre_clahe | 0.0136 | 0.9992 | 0.9970 | 0.9962 | 0.9958 | 121 | 1 | 2 | 1.000 | 54 |
| pre_denoise | 0.0138 | 0.9993 | 0.9979 | 0.9970 | 0.9958 | 121 | 0 | 0 | 1.000 | 4408 |
| pre_uvdoc | 0.0760 | 0.9564 | 0.9800 | 0.9922 | 0.9900 | 121 | 1 | 66 | 9.2e-19 | 753 |
| pre_gated | 0.0138 | 0.9992 | 0.9970 | 0.9962 | 0.9958 | 121 | 0 | 2 | 0.500 | 34 |
| pre_gated_uvdoc | 0.0138 | 0.9992 | 0.9970 | 0.9962 | 0.9958 | 121 | 0 | 2 | 0.500 | 35 |

**synth:lowdpi** (121 pages)

| arm | page CER | bag-of-words F1 | numeric recall | numeric precision | critical fields exact | docs | wins | losses | p (CER vs v6s) | extra ms/page |
|---|---|---|---|---|---|---|---|---|---|---|
| v6s | 0.0467 | 0.9711 | 0.9889 | 0.9873 | 0.9908 | 0 | 0 | 0 | - | - |
| v6m | 0.1347 | 0.9131 | 0.9689 | 0.9748 | 0.9825 | 121 | 6 | 15 | 0.078 | - |
| v5en | 0.1424 | 0.9179 | 0.9634 | 0.9651 | 0.9708 | 121 | 11 | 23 | 0.058 | - |
| crnn | 0.2233 | 0.0757 | 0.5313 | 0.5834 | 0.8567 | 121 | 0 | 121 | 7.5e-37 | - |
| viptr | 0.2082 | 0.0757 | 0.5313 | 0.5753 | 0.8608 | 121 | 0 | 121 | 7.5e-37 | - |
| tess_fast | 0.0455 | 0.9241 | 0.9473 | 0.9409 | 0.9333 | 121 | 4 | 83 | 3.0e-20 | - |
| tess_best | 0.0508 | 0.9295 | 0.9634 | 0.9426 | 0.9542 | 121 | 7 | 74 | 3.2e-15 | - |
| v6m_det+rec | 0.0318 | 0.9876 | 0.9851 | 0.9814 | 0.9825 | 121 | 26 | 10 | 0.011 | 151236 |
| tess_fast_page | 0.1923 | 0.7196 | 0.8022 | 0.8157 | 0.7850 | 121 | 12 | 91 | 3.5e-16 | 62299 |
| tess_best_page | 0.2420 | 0.6731 | 0.7337 | 0.6984 | 0.6633 | 121 | 12 | 97 | 1.1e-17 | 105990 |
| hyb_rep_0.6 | 0.0356 | 0.9670 | 0.9898 | 0.9839 | 0.9908 | 121 | 2 | 1 | 1.000 | - |
| hyb_rep_if_higher_0.98 | 0.0458 | 0.9708 | 0.9889 | 0.9877 | 0.9908 | 121 | 3 | 0 | 0.250 | - |
| pre_deskew | 0.0469 | 0.9701 | 0.9881 | 0.9864 | 0.9892 | 121 | 0 | 1 | 1.000 | 17 |
| pre_clahe | 0.0447 | 0.9716 | 0.9889 | 0.9868 | 0.9883 | 121 | 7 | 5 | 0.774 | 20 |
| pre_denoise | 0.0477 | 0.9695 | 0.9885 | 0.9873 | 0.9892 | 121 | 4 | 12 | 0.077 | 1285 |
| pre_uvdoc | 0.1721 | 0.8625 | 0.9562 | 0.9669 | 0.9700 | 121 | 3 | 65 | 3.6e-16 | 501 |
| pre_gated | 0.0463 | 0.9695 | 0.9872 | 0.9847 | 0.9875 | 121 | 1 | 4 | 0.375 | 96 |
| pre_gated_uvdoc | 0.0463 | 0.9695 | 0.9872 | 0.9847 | 0.9875 | 121 | 1 | 4 | 0.375 | 95 |

**synth:blur** (121 pages)

| arm | page CER | bag-of-words F1 | numeric recall | numeric precision | critical fields exact | docs | wins | losses | p (CER vs v6s) | extra ms/page |
|---|---|---|---|---|---|---|---|---|---|---|
| v6s | 0.0398 | 0.9730 | 0.9889 | 0.9898 | 0.9900 | 0 | 0 | 0 | - | - |
| v6m | 0.1579 | 0.8920 | 0.9728 | 0.9841 | 0.9933 | 121 | 15 | 16 | 1.000 | - |
| v5en | 0.2028 | 0.8769 | 0.9592 | 0.9779 | 0.9842 | 121 | 9 | 22 | 0.029 | - |
| crnn | 0.2955 | 0.0753 | 0.5296 | 0.5968 | 0.8558 | 121 | 0 | 121 | 7.5e-37 | - |
| viptr | 0.2244 | 0.0755 | 0.5304 | 0.5795 | 0.8583 | 121 | 0 | 121 | 7.5e-37 | - |
| tess_fast | 0.1235 | 0.8328 | 0.9149 | 0.8962 | 0.8858 | 121 | 2 | 71 | 5.7e-19 | - |
| tess_best | 0.1182 | 0.8639 | 0.9205 | 0.8719 | 0.8875 | 121 | 5 | 58 | 1.7e-12 | - |
| v6m_det+rec | 0.0507 | 0.9714 | 0.9915 | 0.9962 | 0.9967 | 121 | 29 | 11 | 0.006 | 123038 |
| tess_fast_page | 0.0604 | 0.8561 | 0.8613 | 0.8839 | 0.8258 | 121 | 12 | 71 | 2.4e-11 | 75949 |
| tess_best_page | 0.0641 | 0.8813 | 0.8813 | 0.8836 | 0.8592 | 121 | 16 | 67 | 1.4e-08 | 124299 |
| hyb_rep_0.6 | 0.0370 | 0.9719 | 0.9894 | 0.9868 | 0.9900 | 121 | 3 | 0 | 0.250 | - |
| hyb_rep_if_higher_0.98 | 0.0386 | 0.9730 | 0.9889 | 0.9889 | 0.9900 | 121 | 5 | 0 | 0.062 | - |
| pre_deskew | 0.0389 | 0.9728 | 0.9877 | 0.9885 | 0.9900 | 121 | 4 | 5 | 1.000 | 60 |
| pre_clahe | 0.0309 | 0.9773 | 0.9813 | 0.9780 | 0.9867 | 121 | 11 | 26 | 0.020 | 56 |
| pre_denoise | 0.2012 | 0.7999 | 0.8847 | 0.8946 | 0.8858 | 121 | 5 | 64 | 4.1e-14 | 4361 |
| pre_uvdoc | 0.1172 | 0.8953 | 0.9655 | 0.9713 | 0.9708 | 121 | 4 | 58 | 2.6e-13 | 721 |
| pre_gated | 0.0289 | 0.9775 | 0.9817 | 0.9784 | 0.9867 | 121 | 11 | 20 | 0.150 | 45 |
| pre_gated_uvdoc | 0.0289 | 0.9775 | 0.9817 | 0.9784 | 0.9867 | 121 | 11 | 20 | 0.150 | 44 |

**synth:noise** (121 pages)

| arm | page CER | bag-of-words F1 | numeric recall | numeric precision | critical fields exact | docs | wins | losses | p (CER vs v6s) | extra ms/page |
|---|---|---|---|---|---|---|---|---|---|---|
| v6s | 0.0277 | 0.9721 | 0.9800 | 0.9792 | 0.9783 | 0 | 0 | 0 | - | - |
| v6m | 0.0258 | 0.9916 | 0.9936 | 0.9936 | 0.9933 | 121 | 42 | 13 | 1.1e-04 | - |
| v5en | 0.0274 | 0.9845 | 0.9860 | 0.9814 | 0.9850 | 121 | 40 | 32 | 0.410 | - |
| crnn | 0.1650 | 0.0713 | 0.5228 | 0.5564 | 0.9025 | 121 | 0 | 121 | 7.5e-37 | - |
| viptr | 0.1566 | 0.0741 | 0.5274 | 0.5639 | 0.8967 | 121 | 0 | 121 | 7.5e-37 | - |
| tess_fast | 0.0497 | 0.8165 | 0.8745 | 0.8631 | 0.8950 | 121 | 0 | 121 | 7.5e-37 | - |
| tess_best | 0.0381 | 0.9055 | 0.9545 | 0.9452 | 0.9633 | 121 | 1 | 119 | 1.8e-34 | - |
| v6m_det+rec | 0.0261 | 0.9906 | 0.9936 | 0.9932 | 0.9942 | 121 | 46 | 20 | 0.002 | 164201 |
| tess_fast_page | 0.0433 | 0.8065 | 0.8179 | 0.7979 | 0.8150 | 121 | 9 | 112 | 9.2e-24 | 59176 |
| tess_best_page | 0.0371 | 0.8617 | 0.8762 | 0.8569 | 0.8500 | 121 | 10 | 111 | 1.0e-22 | 94263 |
| hyb_rep_0.6 | 0.0277 | 0.9721 | 0.9800 | 0.9792 | 0.9783 | 121 | 0 | 0 | 1.000 | - |
| hyb_rep_if_higher_0.98 | 0.0277 | 0.9722 | 0.9817 | 0.9809 | 0.9817 | 121 | 5 | 1 | 0.219 | - |
| pre_deskew | 0.0277 | 0.9720 | 0.9796 | 0.9788 | 0.9783 | 121 | 1 | 1 | 1.000 | 49 |
| pre_clahe | 0.0266 | 0.9856 | 0.9736 | 0.9711 | 0.9517 | 121 | 31 | 43 | 0.201 | 49 |
| pre_denoise | 0.0303 | 0.9732 | 0.9592 | 0.9809 | 0.9633 | 121 | 23 | 74 | 2.0e-07 | 3729 |
| pre_uvdoc | 0.1297 | 0.8973 | 0.9562 | 0.9603 | 0.9567 | 121 | 10 | 84 | 1.0e-15 | 559 |
| pre_gated | 0.0279 | 0.9783 | 0.9732 | 0.9707 | 0.9525 | 121 | 24 | 53 | 0.001 | 3737 |
| pre_gated_uvdoc | 0.0279 | 0.9783 | 0.9732 | 0.9707 | 0.9525 | 121 | 24 | 53 | 0.001 | 3791 |

**synth:skew** (121 pages)

| arm | page CER | bag-of-words F1 | numeric recall | numeric precision | critical fields exact | docs | wins | losses | p (CER vs v6s) | extra ms/page |
|---|---|---|---|---|---|---|---|---|---|---|
| v6s | 0.5341 | 0.9986 | 0.9936 | 0.9915 | 0.9975 | 0 | 0 | 0 | - | - |
| v6m | 0.5339 | 0.9966 | 0.9936 | 0.9923 | 0.9975 | 121 | 8 | 6 | 0.791 | - |
| v5en | 0.5337 | 0.9893 | 0.9919 | 0.9911 | 0.9983 | 121 | 14 | 8 | 0.286 | - |
| crnn | 0.5871 | 0.0759 | 0.5328 | 0.5684 | 0.9150 | 121 | 0 | 121 | 7.5e-37 | - |
| viptr | 0.5754 | 0.0758 | 0.5324 | 0.5685 | 0.8992 | 121 | 0 | 121 | 7.5e-37 | - |
| tess_fast | 0.5342 | 0.9983 | 0.9859 | 0.9797 | 0.9867 | 121 | 6 | 22 | 0.004 | - |
| tess_best | 0.5342 | 0.9981 | 0.9902 | 0.9881 | 0.9958 | 121 | 7 | 24 | 0.003 | - |
| v6m_det+rec | 0.5362 | 0.9988 | 0.9940 | 0.9928 | 0.9975 | 121 | 26 | 35 | 0.306 | 99976 |
| tess_fast_page | 0.5979 | 0.7934 | 0.8576 | 0.8871 | 0.8825 | 121 | 36 | 80 | 5.4e-05 | 51891 |
| tess_best_page | 0.5984 | 0.7849 | 0.8734 | 0.8955 | 0.9017 | 121 | 33 | 82 | 5.6e-06 | 69278 |
| hyb_rep_0.6 | 0.5341 | 0.9986 | 0.9936 | 0.9915 | 0.9975 | 121 | 0 | 0 | 1.000 | - |
| hyb_rep_if_higher_0.98 | 0.5341 | 0.9986 | 0.9936 | 0.9919 | 0.9975 | 121 | 1 | 0 | 1.000 | - |
| pre_deskew | 0.5433 | 0.9986 | 0.9923 | 0.9902 | 0.9967 | 121 | 35 | 79 | 4.6e-05 | 63 |
| pre_clahe | 0.5349 | 0.9986 | 0.9928 | 0.9898 | 0.9958 | 121 | 7 | 14 | 0.189 | 56 |
| pre_denoise | 0.5342 | 0.9986 | 0.9936 | 0.9915 | 0.9975 | 121 | 4 | 10 | 0.180 | 4570 |
| pre_uvdoc | 0.5503 | 0.9050 | 0.9322 | 0.9605 | 0.9892 | 121 | 34 | 83 | 6.8e-06 | 781 |
| pre_gated | 0.5433 | 0.9986 | 0.9919 | 0.9898 | 0.9967 | 121 | 35 | 79 | 4.6e-05 | 93 |
| pre_gated_uvdoc | 0.5494 | 0.9048 | 0.9322 | 0.9601 | 0.9900 | 121 | 34 | 83 | 6.8e-06 | 772 |

**synth:curved** (121 pages)

| arm | page CER | bag-of-words F1 | numeric recall | numeric precision | critical fields exact | docs | wins | losses | p (CER vs v6s) | extra ms/page |
|---|---|---|---|---|---|---|---|---|---|---|
| v6s | 0.5110 | 0.6968 | 0.9345 | 0.9955 | 0.9942 | 0 | 0 | 0 | - | - |
| v6m | 0.6126 | 0.5923 | 0.9111 | 0.9885 | 0.9917 | 121 | 8 | 42 | 1.2e-06 | - |
| v5en | 0.6265 | 0.5781 | 0.9098 | 0.9935 | 0.9925 | 121 | 11 | 39 | 9.0e-05 | - |
| crnn | 0.6104 | 0.0775 | 0.5317 | 0.6207 | 0.8600 | 121 | 0 | 121 | 7.5e-37 | - |
| viptr | 0.5933 | 0.0774 | 0.5317 | 0.6170 | 0.8625 | 121 | 0 | 121 | 7.5e-37 | - |
| tess_fast | 0.4957 | 0.7295 | 0.9285 | 0.9772 | 0.9792 | 121 | 28 | 30 | 0.896 | - |
| tess_best | 0.4960 | 0.7289 | 0.9324 | 0.9852 | 0.9858 | 121 | 22 | 32 | 0.220 | - |
| v6m_det+rec | 0.6090 | 0.6023 | 0.9166 | 0.9935 | 0.9975 | 121 | 16 | 56 | 2.4e-06 | 96923 |
| tess_fast_page | 0.3158 | 0.8204 | 0.8894 | 0.8421 | 0.8658 | 121 | 51 | 55 | 0.771 | 74658 |
| tess_best_page | 0.3136 | 0.8214 | 0.8937 | 0.8523 | 0.8692 | 121 | 51 | 56 | 0.699 | 124652 |
| hyb_rep_0.6 | 0.4981 | 0.7145 | 0.9366 | 0.9955 | 0.9942 | 121 | 9 | 0 | 0.004 | - |
| hyb_rep_if_higher_0.98 | 0.4963 | 0.7252 | 0.9379 | 0.9964 | 0.9942 | 121 | 13 | 1 | 0.002 | - |
| pre_deskew | 0.5131 | 0.7114 | 0.9392 | 0.9955 | 0.9967 | 121 | 37 | 49 | 0.235 | 57 |
| pre_clahe | 0.5110 | 0.6978 | 0.9353 | 0.9950 | 0.9950 | 121 | 18 | 13 | 0.473 | 55 |
| pre_denoise | 0.5103 | 0.6984 | 0.9341 | 0.9950 | 0.9942 | 121 | 15 | 7 | 0.134 | 4289 |
| pre_uvdoc | 0.3270 | 0.8888 | 0.9719 | 0.9858 | 0.9925 | 121 | 49 | 55 | 0.624 | 673 |
| pre_gated | 0.5091 | 0.7088 | 0.9375 | 0.9937 | 0.9950 | 121 | 32 | 39 | 0.477 | 71 |
| pre_gated_uvdoc | 0.3394 | 0.8639 | 0.9681 | 0.9840 | 0.9892 | 121 | 41 | 40 | 1.000 | 539 |

**synth:jpeg** (121 pages)

| arm | page CER | bag-of-words F1 | numeric recall | numeric precision | critical fields exact | docs | wins | losses | p (CER vs v6s) | extra ms/page |
|---|---|---|---|---|---|---|---|---|---|---|
| v6s | 0.0480 | 0.9491 | 0.9621 | 0.9593 | 0.9533 | 0 | 0 | 0 | - | - |
| v6m | 0.1321 | 0.8753 | 0.9587 | 0.9637 | 0.9667 | 121 | 32 | 24 | 0.350 | - |
| v5en | 0.1847 | 0.8642 | 0.9362 | 0.9491 | 0.9508 | 121 | 33 | 26 | 0.435 | - |
| crnn | 0.2246 | 0.0748 | 0.5291 | 0.5733 | 0.8592 | 121 | 0 | 121 | 7.5e-37 | - |
| viptr | 0.2098 | 0.0749 | 0.5300 | 0.5708 | 0.8567 | 121 | 0 | 121 | 7.5e-37 | - |
| tess_fast | 0.0389 | 0.9300 | 0.9417 | 0.9350 | 0.9333 | 121 | 26 | 61 | 2.2e-04 | - |
| tess_best | 0.0451 | 0.9243 | 0.9519 | 0.9248 | 0.9417 | 121 | 27 | 49 | 0.015 | - |
| v6m_det+rec | 0.0406 | 0.9483 | 0.9728 | 0.9687 | 0.9667 | 121 | 43 | 14 | 1.5e-04 | 110416 |
| tess_fast_page | 0.0358 | 0.8950 | 0.9179 | 0.9052 | 0.9075 | 121 | 28 | 68 | 5.5e-05 | 53707 |
| tess_best_page | 0.0471 | 0.8812 | 0.9256 | 0.8914 | 0.9108 | 121 | 33 | 44 | 0.254 | 98395 |
| hyb_rep_0.6 | 0.0354 | 0.9497 | 0.9634 | 0.9549 | 0.9533 | 121 | 2 | 0 | 0.500 | - |
| hyb_rep_if_higher_0.98 | 0.0479 | 0.9493 | 0.9621 | 0.9593 | 0.9533 | 121 | 5 | 0 | 0.062 | - |
| pre_deskew | 0.0480 | 0.9491 | 0.9621 | 0.9593 | 0.9533 | 121 | 0 | 0 | 1.000 | 34 |
| pre_clahe | 0.0642 | 0.9333 | 0.9549 | 0.9513 | 0.9492 | 121 | 14 | 48 | 1.7e-05 | 33 |
| pre_denoise | 0.0275 | 0.9594 | 0.9660 | 0.9611 | 0.9567 | 121 | 34 | 21 | 0.105 | 2493 |
| pre_uvdoc | 0.1674 | 0.8517 | 0.9324 | 0.9408 | 0.9433 | 121 | 14 | 71 | 2.4e-10 | 682 |
| pre_gated | 0.0556 | 0.9436 | 0.9583 | 0.9547 | 0.9517 | 121 | 6 | 17 | 0.035 | 18 |
| pre_gated_uvdoc | 0.0556 | 0.9436 | 0.9583 | 0.9547 | 0.9517 | 121 | 6 | 17 | 0.035 | 17 |

**synth:faded** (121 pages)

| arm | page CER | bag-of-words F1 | numeric recall | numeric precision | critical fields exact | docs | wins | losses | p (CER vs v6s) | extra ms/page |
|---|---|---|---|---|---|---|---|---|---|---|
| v6s | 0.0120 | 0.9995 | 0.9974 | 0.9970 | 0.9967 | 0 | 0 | 0 | - | - |
| v6m | 0.0120 | 0.9992 | 0.9957 | 0.9966 | 0.9958 | 121 | 6 | 11 | 0.332 | - |
| v5en | 0.0120 | 0.9994 | 0.9932 | 0.9936 | 0.9992 | 121 | 13 | 11 | 0.839 | - |
| crnn | 0.1391 | 0.0759 | 0.5325 | 0.5686 | 0.9533 | 121 | 0 | 121 | 7.5e-37 | - |
| viptr | 0.1318 | 0.0759 | 0.5313 | 0.5677 | 0.9325 | 121 | 0 | 121 | 7.5e-37 | - |
| tess_fast | 0.0124 | 0.9961 | 0.9889 | 0.9852 | 0.9833 | 121 | 1 | 47 | 3.5e-13 | - |
| tess_best | 0.0122 | 0.9979 | 0.9953 | 0.9936 | 0.9950 | 121 | 7 | 29 | 3.1e-04 | - |
| v6m_det+rec | 0.0140 | 0.9992 | 0.9940 | 0.9957 | 0.9942 | 121 | 9 | 16 | 0.230 | 171667 |
| tess_fast_page | 0.0492 | 0.9660 | 0.7882 | 0.9110 | 0.7550 | 121 | 11 | 72 | 3.9e-12 | 45614 |
| tess_best_page | 0.0492 | 0.9659 | 0.7933 | 0.9183 | 0.7608 | 121 | 11 | 74 | 1.3e-12 | 75907 |
| hyb_rep_0.6 | 0.0120 | 0.9995 | 0.9974 | 0.9970 | 0.9967 | 121 | 0 | 0 | 1.000 | - |
| hyb_rep_if_higher_0.98 | 0.0120 | 0.9995 | 0.9974 | 0.9970 | 0.9967 | 121 | 0 | 0 | 1.000 | - |
| pre_deskew | 0.0120 | 0.9995 | 0.9974 | 0.9970 | 0.9967 | 121 | 0 | 0 | 1.000 | 48 |
| pre_clahe | 0.0112 | 0.9972 | 0.9911 | 0.9915 | 0.9950 | 121 | 4 | 31 | 3.5e-06 | 49 |
| pre_denoise | 0.0169 | 0.9661 | 0.9898 | 0.9852 | 0.9825 | 121 | 3 | 30 | 1.4e-06 | 3648 |
| pre_uvdoc | 0.0910 | 0.9424 | 0.9872 | 0.9936 | 0.9958 | 121 | 2 | 55 | 2.3e-14 | 545 |
| pre_gated | 0.0112 | 0.9972 | 0.9911 | 0.9915 | 0.9950 | 121 | 4 | 31 | 3.5e-06 | 48 |
| pre_gated_uvdoc | 0.0112 | 0.9972 | 0.9911 | 0.9915 | 0.9950 | 121 | 4 | 31 | 3.5e-06 | 49 |

**synth:tiny_print** (152 pages)

| arm | page CER | bag-of-words F1 | numeric recall | numeric precision | critical fields exact | docs | wins | losses | p (CER vs v6s) | extra ms/page |
|---|---|---|---|---|---|---|---|---|---|---|
| v6s | 0.1857 | 0.9158 | 0.9140 | 0.9452 | 0.9384 | 0 | 0 | 0 | - | - |
| v6m | 0.2770 | 0.8512 | 0.8631 | 0.9248 | 0.9366 | 19 | 2 | 17 | 7.3e-04 | - |
| v5en | 0.3051 | 0.8399 | 0.8209 | 0.8883 | 0.8864 | 19 | 0 | 19 | 3.8e-06 | - |
| crnn | 0.3679 | 0.0035 | 0.0000 | 0.0000 | 0.3820 | 19 | 0 | 19 | 3.8e-06 | - |
| viptr | 0.3379 | 0.0035 | 0.0000 | 0.0000 | 0.2967 | 19 | 0 | 19 | 3.8e-06 | - |
| tess_fast | 0.2024 | 0.8511 | 0.8409 | 0.8424 | 0.8327 | 19 | 2 | 17 | 7.3e-04 | - |
| tess_best | 0.2028 | 0.8683 | 0.8620 | 0.8192 | 0.8442 | 19 | 2 | 17 | 7.3e-04 | - |
| v6m_det+rec | 0.2002 | 0.9172 | 0.9115 | 0.9502 | 0.9463 | 19 | 3 | 16 | 0.004 | 307030 |
| tess_fast_page | 0.2169 | 0.7786 | 0.7539 | 0.7273 | 0.7113 | 19 | 3 | 16 | 0.004 | 143289 |
| tess_best_page | 0.2325 | 0.7748 | 0.7553 | 0.6584 | 0.7051 | 19 | 3 | 16 | 0.004 | 228136 |
| hyb_rep_0.6 | 0.1758 | 0.9178 | 0.9175 | 0.9366 | 0.9384 | 19 | 7 | 0 | 0.016 | - |
| hyb_rep_if_higher_0.98 | 0.1816 | 0.9207 | 0.9161 | 0.9449 | 0.9384 | 19 | 9 | 1 | 0.021 | - |
| pre_deskew | 0.1798 | 0.9174 | 0.9140 | 0.9424 | 0.9384 | 19 | 17 | 2 | 7.3e-04 | 52 |
| pre_clahe | 0.1855 | 0.9180 | 0.9168 | 0.9426 | 0.9322 | 19 | 9 | 10 | 1.000 | 53 |
| pre_denoise | 0.2232 | 0.8675 | 0.8480 | 0.8820 | 0.8398 | 19 | 0 | 19 | 3.8e-06 | 4013 |
| pre_uvdoc | 0.2823 | 0.7983 | 0.8209 | 0.8789 | 0.8530 | 19 | 2 | 17 | 7.3e-04 | 664 |
| pre_gated | 0.1788 | 0.9200 | 0.9185 | 0.9430 | 0.9349 | 19 | 17 | 2 | 7.3e-04 | 547 |
| pre_gated_uvdoc | 0.1544 | 0.9170 | 0.9178 | 0.9349 | 0.9243 | 19 | 19 | 0 | 3.8e-06 | 706 |

### 1d. Gate triggers by synthetic defect (share of pages where each gate fired)

| defect | pages | deskew | clahe | denoise | uvdoc |
|---|---|---|---|---|---|
| blur | 240 | 0.00 | 0.88 | 0.00 | 0.00 |
| clean | 240 | 0.00 | 0.70 | 0.00 | 0.00 |
| curved | 240 | 0.67 | 0.68 | 0.00 | 0.80 |
| faded | 240 | 0.00 | 0.99 | 0.00 | 0.00 |
| jpeg | 240 | 0.00 | 0.67 | 0.00 | 0.00 |
| lowdpi | 240 | 0.00 | 0.65 | 0.04 | 0.00 |
| noise | 240 | 0.00 | 0.64 | 1.00 | 0.00 |
| real_scan | 199 | 0.11 | 0.55 | 0.00 | 0.14 |
| receipt | 652 | 0.09 | 0.59 | 0.00 | 0.10 |
| skew | 240 | 1.00 | 0.66 | 0.00 | 1.00 |

### 1e. OmniDocBench English text regions (detector on the region crop, all regions)

| slice | regions | v6s | v6m | v5en | crnn | viptr | tess_fast | tess_best | tess_best_block (CER / WER) |
|---|---|---|---|---|---|---|---|---|---|
| all | 3934 | 0.016 / 0.088 | 0.016 / 0.087 | 0.020 / 0.092 | 0.164 / 0.992 | 0.155 / 0.992 | 0.022 / 0.098 | 0.022 / 0.097 | 0.022 / 0.099 |
| hard sources | 2400 | 0.019 / 0.095 | 0.019 / 0.093 | 0.024 / 0.099 | 0.166 / 0.993 | 0.158 / 0.992 | 0.027 / 0.106 | 0.027 / 0.106 | 0.027 / 0.108 |
| other sources | 1534 | 0.011 / 0.077 | 0.011 / 0.075 | 0.013 / 0.080 | 0.161 / 0.991 | 0.149 / 0.991 | 0.014 / 0.082 | 0.014 / 0.082 | 0.014 / 0.082 |

| challenger | pages (groups) | wins | losses | p | CI (CER reduction vs v6s) |
|---|---|---|---|---|---|
| v6m | 656 | 121 | 62 | 1.5e-05 | [-0.0003, +0.0032] |
| v5en | 656 | 88 | 183 | 8.0e-09 | [-0.0103, -0.0014] |
| crnn | 656 | 1 | 643 | 1.8e-191 | [-0.1563, -0.1449] |
| viptr | 656 | 3 | 642 | 6.1e-187 | [-0.1450, -0.1327] |
| tess_fast | 656 | 86 | 228 | 5.5e-16 | [-0.0168, -0.0064] |
| tess_best | 656 | 90 | 228 | 5.8e-15 | [-0.0161, -0.0056] |
| tess_best_block | 656 | 108 | 210 | 1.1e-08 | [-0.0173, -0.0043] |

### 1f. Speed and memory (one thread, own process; Intel(R) Xeon(R) 6975P-C)

| component | items | load ms | mean ms | p50 ms | p95 ms | peak RSS MB |
|---|---|---|---|---|---|---|
| det_s | 24 | 33 | 1531.5 | 1226.0 | 2616.8 | 1960 |
| det_m | 24 | 123 | 18482.0 | 14510.6 | 33042.7 | 1960 |
| uvdoc | 8 | 79 | 272.4 | 248.5 | 300.5 | 1960 |
| v6s | 600 | 57 | 12.8 | 8.2 | 37.0 | 1960 |
| v6m | 600 | 153 | 733.8 | 486.0 | 2118.9 | 1960 |
| v5en | 600 | 61 | 15.1 | 7.7 | 51.6 | 1960 |
| crnn | 600 | 2258 | 2.3 | 1.5 | 5.8 | 1960 |
| viptr | 600 | 3537 | 16.2 | 11.5 | 37.4 | 1960 |
| tess_fast | 600 | 109 | 6.9 | 4.7 | 18.4 | 1960 |
| tess_best | 600 | 95 | 12.7 | 8.6 | 34.9 | 1960 |

Merged records: 2771 pages (2771 with every crop arm), 3934 regions; crop-count mismatches between arm-group jobs: 0.

**Reading notes:**
- **CRNN and VIPTR:** OnnxTR's docTR models are word recognizers. On line crops they drop the spaces between words, so their WER (about 0.94) and bag-of-words F1 mostly measure missing spaces. Their CER (0.25-0.27) is still clearly worse than PP-OCRv6.
- **`synth:skew` crops (CER 0.54 for every engine):** the axis-aligned GT box of a rotated word overlaps neighbouring lines, so line-level GT assignment fails the same way for every engine. Use the end-to-end page table and the deskew arm for skew.

**Verdict, gap 1:**
- **Keep PP-OCRv6 small** (docling.rs default), det + rec. On the test split:
  - same-crop CER 0.111, WER 0.160, numeric-token exact 0.897;
  - end to end: page CER 0.161, critical-field exact 0.973.
  - Cost: 12.8 ms per line crop and 1.5 s per page for detection (one thread).
- **PP-OCRv6 medium:** not worth it as default.
  - Slightly better on receipts (field exact 0.974 vs 0.972) and noisy pages, but it collapses on long dense lines: synthetic page CER 0.203 vs 0.154; tiny print 0.234 vs 0.138.
  - 57x slower per line crop (734 ms) and 12x slower to detect (18.5 s per page).
- **en PP-OCRv5 mobile:** worse (CER 0.171; 168 wins / 350 losses). Reject.
- **OnnxTR CRNN and VIPTR (line crops):** worse on every slice (0 wins). Reject.
- **Tesseract 5 fast / best, apt:**
  - Crops: CER 0.126 / 0.125, numeric exact 0.79 / 0.82, 13-17 wins vs about 555 losses.
  - Whole page: CER 0.185 / 0.191, critical fields 0.79.
  - Slightly better only on curved and JPEG pages. Reject as a replacement.
- **Tesseract only on low-confidence lines (threshold 0.6, chosen on dev):**
  - Same-crop CER 0.1070 vs 0.1107 (21 vs 46 documents, p = 0.003, CI includes 0).
  - End to end: page CER 0.1567 vs 0.1607, 50 vs 120 documents (more documents get worse, p = 8e-8).
  - It helps synthetic pages (10 vs 0) but hurts FUNSD and receipts. Not adopted.
- **Preprocessing:**
  - Always-on deskew and CLAHE: no gain. Always-on denoise and always-on UVDoc: worse (page CER 0.178 and 0.205).
  - Gated deskew/CLAHE/denoise: neutral.
  - Gated UVDoc (curved or skewed pages only): lowest overall page CER, 0.143 vs 0.161. But the per-document sign test is not significant (147 vs 183, p = 0.054); the gain comes from a few badly warped pages, and it adds about 0.5 s per page.
  - Worth a targeted follow-up on real curved scans; not a default yet.

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
