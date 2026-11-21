# Round 4 media tests (repo 2, media/)

Status, 2026-11-21: this file holds the parts that have finished.
- Still being re-run: OCR (gap 1), charts (gap 2), forms + FFDetr (gap 3) and the LibreOffice route for Word formulas. Their sections are added when they finish (workflow `media-r4.yml`).
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
