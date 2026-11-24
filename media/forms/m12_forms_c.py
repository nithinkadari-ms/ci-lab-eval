"""Milestone 12, round c: choose the simulator fit's regularisation C on FUNSD's training forms (validation), not on the
test forms. Rule fixed before the run: among C in (1, 0.1, 0.01, 0.001), keep the C with the highest pair F1 on the
149 FUNSD training forms whose share of blanks wrongly filled there is not above the nearest-label rule's; report
that C on the 50 test forms. Nothing is fitted on FUNSD. Writes the weights and 12 held-out simulated forms with the
Python outputs for every C. usage: m12_forms_c.py OUTDIR [N_SIM]"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ocr"))
import m12_forms as m12  # noqa: E402
import m12_forms_b as mb  # noqa: E402
import run_forms as rf  # noqa: E402
from common import pfmt, sign_test  # noqa: E402

CS = (1.0, 0.1, 0.01, 0.001)


def blanks(rs):
    return sum(x["filled"] for x in rs) / max(1, sum(x["blank"] for x in rs))


def main():
    out = sys.argv[1]
    n_sim = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    os.makedirs(out, exist_ok=True)
    sims = [mb.sim_doc(s) for s in range(n_sim)]
    tr, tu = sims[: int(0.8 * n_sim)], sims[int(0.8 * n_sim):]
    import engines
    import ppocr
    det = ppocr.Detector(engines.P["det_s"])
    rec = ppocr.Recognizer(engines.P["rec_s"], ppocr.load_dict(engines.P["dict_s"]))
    fdocs = m12.funsd_docs(det, rec)
    ftrain = [d for d in fdocs if d["split"] == "train"]
    ftest = [d for d in fdocs if d["split"] == "test"]
    nn_val, nn_test = m12.nn(ftrain), m12.nn(ftest)
    md = ["## Milestone 12c: simulator regularisation chosen on FUNSD training forms (validation only)", "",
          "| C | threshold | val pair F1 | val blanks wrongly filled | test pair P | test pair R | test pair F1 | "
          "test blanks wrongly filled | sim held-out F1 |", "|---|---|---|---|---|---|---|---|---|"]
    md.append(f"| nn (rule) | - | {rf.prf(nn_val)[2]:.3f} | {blanks(nn_val):.3f} | {rf.prf(nn_test)[0]:.3f} | "
              f"{rf.prf(nn_test)[1]:.3f} | {rf.prf(nn_test)[2]:.3f} | {blanks(nn_test):.3f} | - |")
    rows, test_res = {}, {}
    for C in CS:
        m, th = mb.fit_c(tr, tu, C)
        val = m12.score(m, th, ftrain)
        test = m12.score(m, th, ftest)
        sim = [rf.evaluate(d, rf.assign(d["lines"], d["cands"], m.decision_function(m12.xy(d)[0]), th))
               for d in tu if d["cands"]]
        rows[C] = {"th": th, "val_f1": rf.prf(val)[2], "val_blank": blanks(val), "test": rf.prf(test),
                   "test_blank": blanks(test), "sim_f1": rf.prf(sim)[2]}
        test_res[C] = test
        p, r, f = rf.prf(test)
        md.append(f"| {C:g} | {th:.2f} | {rows[C]['val_f1']:.3f} | {rows[C]['val_blank']:.3f} | {p:.3f} | {r:.3f} | "
                  f"{f:.3f} | {rows[C]['test_blank']:.3f} | {rows[C]['sim_f1']:.3f} |")
        json.dump(m12.weights(m, th, f"line-level form simulator v2 (m12_forms_b.py), C = {C:g}"),
                  open(os.path.join(out, f"form_matcher_sim2_C{C:g}.json"), "w"), indent=1)
        samples = []
        for d in tu[:12]:
            X = rf.feats(d["lines"], d["cands"], d["lh"], d["W"]) if d["cands"] else np.zeros((0, 31))
            s = m.decision_function(X) if d["cands"] else np.zeros(0)
            pairs = rf.assign(d["lines"], d["cands"], s, th) if d["cands"] else []
            samples.append({"id": d["id"], "W": d["W"], "H": d["H"],
                            "lines": [{"t": L["t"], "box": L["box"], "conf": L["conf"]} for L in d["lines"]],
                            "cands": [[i, j, k] for i, j, k in d["cands"]], "lh": d["lh"], "feats": X.tolist(),
                            "scores": [float(v) for v in s], "pairs": [[int(i), int(j)] for i, j in pairs]})
        json.dump(samples, open(os.path.join(out, f"form_samples_sim2_C{C:g}.json"), "w"))
    allowed = [C for C in CS if rows[C]["val_blank"] <= blanks(nn_val)]
    pick = max(allowed or CS, key=lambda C: rows[C]["val_f1"])
    w, l, p = sign_test([m12.f1_of(x) - m12.f1_of(y) for x, y in zip(test_res[pick], nn_test)])
    md += ["", f"Picked by the rule: C = {pick:g} (allowed: {', '.join(f'{c:g}' for c in allowed) or 'none'}). "
               f"On the test forms vs the nearest-label rule: better on {w}, worse on {l} forms, p = {pfmt(p)}.", ""]
    open(os.path.join(out, "m12_forms_c.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    json.dump({"rows": {f"{C:g}": v for C, v in rows.items()}, "pick": pick, "sign": [w, l, p]},
              open(os.path.join(out, "m12_forms_c.json"), "w"), indent=1)
    print("\n".join(md))


if __name__ == "__main__":
    main()
