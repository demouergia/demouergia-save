from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
SAVE_API_KEY = os.getenv("SAVE_API_KEY", "").strip() or None
SAVE_LAMBDA = float(os.getenv("SAVE_LAMBDA", "0.8"))

CAPS = ["S","H","C","E","I"]

def weights_for(meta: dict) -> dict:
    sector = str(meta.get("sector","")).upper()
    profession = str(meta.get("profession","")).lower()
    w = {"S":1.0,"H":1.0,"C":1.0,"E":1.0,"I":1.0}
    if "CCS" in sector or "CREATIVE" in sector:
        w.update({"S":0.8,"H":1.0,"C":1.2,"E":1.0,"I":0.9})
    if "entrepreneur" in profession or "founder" in profession:
        w.update({"S":1.1,"E":1.1})
    return w

def risk_alphas(meta: dict) -> dict:
    return {"R_precarity":0.3,"R_burnout":0.2,"R_support_access":0.2,"R_shock_exposure":0.3}
