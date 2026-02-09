from __future__ import annotations
from typing import Dict, Any, List
import json
from pathlib import Path

_ARC_PATH = Path(__file__).resolve().parent / "profile_archetypes.json"

def load_archetypes() -> List[dict]:
    data = json.loads(_ARC_PATH.read_text(encoding="utf-8"))
    return data.get("archetypes", [])

def _check_threshold(value: float, rule: dict) -> bool:
    if value is None:
        return False
    if "gte" in rule and not (value >= float(rule["gte"])):
        return False
    if "lte" in rule and not (value <= float(rule["lte"])):
        return False
    return True

def match_archetypes(capital_vector: Dict[str, float], risk_components: Dict[str, float]) -> List[dict]:
    matches: List[dict] = []
    for a in load_archetypes():
        when = a.get("when", {})
        cv_rules = when.get("capital_vector", {})
        rc_rules = when.get("risk_components", {})
        ok = True
        for k, rule in cv_rules.items():
            ok = ok and _check_threshold(float(capital_vector.get(k, 0.0)), rule)
        for k, rule in rc_rules.items():
            ok = ok and _check_threshold(float(risk_components.get(k, 0.0)), rule)
        if ok:
            matches.append(a)
    return matches

def build_profile(
    assessment_id: str,
    profile_id: str,
    meta_public: Dict[str, Any],
    results: Dict[str, Any],
    lang: str = "en",
) -> Dict[str, Any]:
    cv = results.get("capital_vector") or {}
    risk = results.get("risk") or {}
    risk_components = risk.get("components") or {}
    bottlenecks = results.get("bottlenecks") or []

    archetypes = match_archetypes(cv, risk_components)
    primary = archetypes[0] if archetypes else None

    def tr(obj):
        # obj may be {"en":..,"el":..} OR a signal dict with en/el
        if isinstance(obj, dict):
            return obj.get(lang) or obj.get("en") or ""
        return str(obj)

    opportunities = []
    risks = []
    actions = []
    if primary:
        sig = primary.get("signals", {})
        opportunities = [{"code":x.get("code"), "text": tr(x)} for x in (sig.get("opportunity") or [])[:4]]
        risks = [{"code":x.get("code"), "text": tr(x)} for x in (sig.get("risk") or [])[:4]]
        actions = [{"code":x.get("code"), "text": tr(x)} for x in (sig.get("actions") or [])[:6]]

    bn_cards = []
    for b in bottlenecks[:5]:
        bn_cards.append({
            "type": "bottleneck",
            "from": b.get("from"),
            "to": b.get("to"),
            "t": b.get("t"),
            "barrier": b.get("barrier"),
            "t_eff": b.get("t_eff"),
            "priority": b.get("priority"),
        })

    headline = tr(primary.get("label")) if primary else ( "SAVE Profile (generic)" if lang!="el" else "Προφίλ SAVE (γενικό)" )
    if lang == "el":
        summary = (
            f"Κύρια εικόνα: {headline}. "
            f"Κεφάλαια (S,H,C,E,I): {cv}. "
            f"Συνολικός κίνδυνος V={risk.get('V')}. "
            f"Κύρια μονοπάτια βελτίωσης: {[(x.get('from'), x.get('to')) for x in bottlenecks[:3]]}."
        )
    else:
        summary = (
            f"Primary pattern: {headline}. "
            f"Capitals (S,H,C,E,I): {cv}. "
            f"Overall risk V={risk.get('V')}. "
            f"Top improvement paths: {[(x.get('from'), x.get('to')) for x in bottlenecks[:3]]}."
        )

    return {
        "ui": {
            "headline": headline,
            "summary": summary,
            "cards": {
                "opportunities": opportunities,
                "risks": risks,
                "actions": actions,
                "bottlenecks": bn_cards,
            },
            "charts": {
                "radar": {"labels": ["S","H","C","E","I"], "values": [cv.get("S"),cv.get("H"),cv.get("C"),cv.get("E"),cv.get("I")]},
            },
        },
        "data": {
            "assessment_id": assessment_id,
            "profile_id": profile_id,
            "meta_public": meta_public,
            "primary_archetype": (primary.get("id") if primary else None),
            "matched_archetypes": [a.get("id") for a in archetypes],
            "capital_vector": cv,
            "risk": risk,
            "bottlenecks": bottlenecks,
        },
    }
