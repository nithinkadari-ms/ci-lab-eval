# Round 4 media tests (repo 2, media/)

Status, 2026-11-21: this file holds the parts that have finished.
- Still being re-run: OCR (gap 1), PlotQA scoring for charts (gap 2), forms + FFDetr (gap 3) and the LibreOffice route for Word formulas. Their sections are added when they finish (workflow `media-r4.yml`).
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
