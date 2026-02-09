from __future__ import annotations
from typing import Dict, Any
import numpy as np
from .config import CAPS, SAVE_LAMBDA, weights_for, risk_alphas

IDX = {c:i for i,c in enumerate(CAPS)}
STOCK_PREFIX = {"S":"S_stock_","H":"H_stock_","C":"C_stock_","E":"E_stock_","I":"I_stock_"}

T_MAP = {
    "S_to_E_opps": ("S","E"),
    "S_to_H_mentoring": ("S","H"),
    "S_to_I_gatekeeper": ("S","I"),
    "H_to_E_pitch": ("H","E"),
    "H_to_E_negotiate": ("H","E"),
    "H_to_S_teamwork": ("H","S"),
    "H_to_I_documentation": ("H","I"),
    "C_to_S_storytelling": ("C","S"),
    "C_to_S_crossdiscipline": ("C","S"),
    "C_to_S_visibility": ("C","S"),
    "C_to_E_monetize": ("C","E"),
    "C_to_E_rights": ("C","E"),
    "C_to_E_adapt": ("C","E"),
    "E_to_S_invest_network": ("E","S"),
    "E_to_H_invest_learning": ("E","H"),
    "E_to_I_tax_admin_capacity": ("E","I"),
    "I_to_E_funding": ("I","E"),
    "I_to_S_participation": ("I","S"),
    "I_to_C_validation": ("I","C"),
    "I_to_C_access": ("I","C"),
}

B_MAP = {
    "B_institutional_complexity": [("I","E"), ("I","S"), ("I","C"), ("I","H"), ("S","I"), ("H","I"), ("C","I"), ("E","I")],
    "B_market_gatekeeping": [("C","E"), ("S","E"), ("H","E")],
    "B_digital_divide": [("S","I"), ("I","S"), ("H","E"), ("I","E"), ("E","I")],
    "B_discrimination_exclusion": [("S","E"), ("H","E"), ("I","E"), ("I","S")],
    "B_CE_gatekeeping": [("C","E")],
}

RISK_KEYS = ["R_precarity","R_burnout","R_support_access","R_shock_exposure"]

# Keys where higher response indicates a *better* state, but the model needs a *risk/negative* indicator.
# We invert these during normalization.
REVERSE_KEYS = {"R_support_access"}
# Keys where higher response indicates a more negative condition but is stored as a stock-like item.
STOCK_REVERSE_KEYS = {"E_stock_debt_limits"}


def norm_0_5(x: Any) -> float:
    """Normalize numeric responses to 0..1.

    SAVER Model 1 uses a 0–5 scale (0 minimum … 5 very good).
    We clamp to 0..5 and return x/5.
    """
    x = float(x)
    x = max(0.0, min(5.0, x))
    return x / 5.0

def normalize_responses(responses: Dict[str, Any]) -> Dict[str, float]:
    out: Dict[str, float] = {}

    def map_yes_no(val: Any):
        if not isinstance(val, str):
            return None
        t = val.strip().lower()
        yes = {"yes", "y", "nai", "ναι", "yes / ναι", "yes / ναι".lower(), "yes / ναi"}
        no = {"no", "n", "oxi", "όχι", "οχι", "no / όχι", "no / οχι"}
        if t in yes:
            return 5.0
        if t in no:
            return 0.0
        return None

    for k, v in responses.items():
        if v is None or v == "":
            continue

        # Map common yes/no (e.g., financial buffer)
        yn = map_yes_no(v)
        if yn is not None:
            v_num = yn
        else:
            v_num = v

        if k == "I_to_E_funding" and isinstance(v_num, str):
            # legacy mapping if you use categorical answers in other forms
            mapping = {"Not eligible/NA": None, "Tried but failed": 2, "Sometimes": 3, "Often": 4}
            vv = mapping.get(v_num)
            if vv is None:
                continue
            out[k] = norm_0_5(vv)
            continue

        try:
            val = norm_0_5(v_num)
        except Exception:
            continue

        # Apply inversions where needed
        if k in REVERSE_KEYS:
            val = 1.0 - val
        if k in STOCK_REVERSE_KEYS:
            val = 1.0 - val

        out[k] = val

    return out


def compute_capital_vector(normed: Dict[str, float]) -> np.ndarray:
    Cvec = np.zeros(5)
    for cap, pref in STOCK_PREFIX.items():
        vals = [v for k,v in normed.items() if k.startswith(pref)]
        Cvec[IDX[cap]] = float(np.mean(vals)) if vals else 0.0
    return Cvec

def compute_T_B(normed: Dict[str, float]):
    T = np.zeros((5,5))
    B = np.zeros((5,5))
    cell_vals = {}
    for k,(a,b) in T_MAP.items():
        if k in normed:
            cell_vals.setdefault((a,b), []).append(normed[k])
    for (a,b), vals in cell_vals.items():
        T[IDX[a], IDX[b]] = float(np.mean(vals))
    for bk, affected in B_MAP.items():
        if bk in normed:
            for (a,b) in affected:
                B[IDX[a], IDX[b]] = max(B[IDX[a], IDX[b]], float(normed[bk]))
    return T, B

def compute_risk(meta: Dict[str, Any], normed: Dict[str, float]) -> dict:
    alphas = risk_alphas(meta)
    V = 0.0
    comps = {}
    for rk in RISK_KEYS:
        val = float(normed.get(rk, 0.0))
        comps[rk] = val
        V += alphas.get(rk, 0.0) * val
    return {"V": float(V), "components": comps, "alphas": alphas, "lambda": SAVE_LAMBDA}

def diagnose(meta: Dict[str, Any], responses: Dict[str, Any]) -> dict:
    normed = normalize_responses(responses)
    Cvec = compute_capital_vector(normed)
    w = weights_for(meta)
    wvec = np.array([w[c] for c in CAPS], dtype=float)
    Avec = Cvec * wvec

    T, B = compute_T_B(normed)
    T_eff = T * (1.0 - B)

    Vvec = Avec @ T_eff
    flow_norm = float(np.sum(np.abs(Vvec)))

    risk = compute_risk(meta, normed)
    save_score = flow_norm - float(risk["lambda"]) * float(risk["V"])

    bottlenecks = []
    for i,a in enumerate(CAPS):
        for j,b in enumerate(CAPS):
            if i==j or T[i,j] <= 0:
                continue
            bottlenecks.append({
                "from": a, "to": b,
                "t": float(T[i,j]),
                "barrier": float(B[i,j]),
                "t_eff": float(T_eff[i,j]),
                "priority": float(Avec[i] * (1.0 - T_eff[i,j])),
            })
    bottlenecks.sort(key=lambda x: x["priority"], reverse=True)
    bottlenecks = bottlenecks[:5]

    return {
        "save_score": round(save_score, 6),
        "responses_norm": {k: round(float(v), 6) for k,v in normed.items()},
        "capital_vector": {c: round(float(Cvec[IDX[c]]), 6) for c in CAPS},
        "weights": {c: round(float(wvec[IDX[c]]), 6) for c in CAPS},
        "risk": {"V": round(float(risk["V"]), 6), "lambda": risk["lambda"], "components": risk["components"], "alphas": risk["alphas"]},
        "bottlenecks": bottlenecks,
    }
