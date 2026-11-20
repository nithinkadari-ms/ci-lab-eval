"""Matrices for the round 3 workflow."""
import json, sys
kind = sys.argv[1]
CDM_MODELS = {"p2t15_fp32": 2, "p2t15_fp16": 2, "p2t15_int16": 3, "p2t15_int8": 2, "p2t15_int8_split": 1,
              "p2t15_int4_b32": 2, "p2t15_int4_b128": 2, "pp_formulanet_plus_s": 1, "unirec_0_1b": 2,
              "doctr_formulanet": 1, "doctr_formulanet_int8": 1, "monkey_s_torch": 4, "monkey_s_onnx_int8": 3}
T1_SYSTEMS = ["logic", "pdfmath", "rustypaper", "kakemono", "gopdfkit"]
T2_SYSTEMS = ["t2_p2t15_int8_1024", "t2_p2t15_fp32_1024", "t2_p2t15_int8_split", "t2_p2t15_fp32_split"]
inc = []
if kind == "acc":
    inc += [{"model": "p2t15_int8", "set": "arxiv", "shard": k, "n": 4} for k in range(4)]
    for m, n in CDM_MODELS.items():
        inc += [{"model": m, "set": "cdm_items", "shard": k, "n": n} for k in range(n)]
elif kind == "cdm":
    for s in list(CDM_MODELS) + T1_SYSTEMS + T2_SYSTEMS:
        inc += [{"system": s, "shard": k, "n": 2} for k in range(2)]
print(json.dumps({"include": inc}))
