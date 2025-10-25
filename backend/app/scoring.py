# app/scoring.py
"""
Scoring module: combines LLM judgments, regex heuristics, spaCy probabilities,
and personalized preference penalties into a transparent Trust Score.

Inputs (expected shapes):
- heuristics: {
    "<Category>": { "delta": float (±), "flags": [str, ...] },
    ...
  }
- llm: {
    "<Category>": { "score": float in [0,1], "reason": str },
    ...
  }
- spacy: {
    "<Category>": float in [0,1],   # optional; may be {}
    ...
  }
- preference_penalties: {
    "<Category>": float (usually negative, e.g., -0.10),
    ...
  }

Output:
{
  "trust_score": float (0..100),
  "risk_level": "High" | "Medium" | "Low",
  "categories": {
    "<Category>": {
      "score": float in [0,1],
      "reason": str,
      "heuristics": {"delta": float, "flags": [...]},
      "spacy_prob": float | None
    },
    ...
  }
}
"""

from typing import Dict, Any
from .config import CATEGORY_WEIGHTS

# ---- Blend weights among sources (tune as needed) ----
# LLM carries most signal; heuristics nudge; spaCy adds corroboration
ALPHA_LLM   = 0.50   # Gemini (primary)
BETA_REGEX  = 0.20   # heuristics delta applied relative to LLM
GAMMA_SPACY = 0.30   # spaCy per-category probability

# Thresholds for final badge (keep in sync with your doc)
RISK_HIGH_MAX   = 39.0   # 0–39 = High
RISK_MEDIUM_MAX = 69.0   # 40–69 = Medium
# 70–100 = Low


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _risk_label(score_0_100: float) -> str:
    if score_0_100 <= RISK_HIGH_MAX:
        return "High"
    if score_0_100 <= RISK_MEDIUM_MAX:
        return "Medium"
    return "Low"


def _safe_llm_score(llm_for_cat: Dict[str, Any]) -> float:
    # Default to 0.5 (neutral) if missing
    try:
        return float(llm_for_cat.get("score", 0.5))
    except Exception:
        return 0.5


def _safe_llm_reason(llm_for_cat: Dict[str, Any], heur_for_cat: Dict[str, Any]) -> str:
    # Prefer LLM reason; fallback to a short heuristic-based phrase
    reason = (llm_for_cat or {}).get("reason")
    if isinstance(reason, str) and reason.strip():
        return reason.strip()
    # Fallback from heuristics flags
    flags = (heur_for_cat or {}).get("flags") or []
    if flags:
        sample = ", ".join(flags[:3])
        return f"Signals detected: {sample}"
    return ""


def _safe_heur_delta(heur_for_cat: Dict[str, Any]) -> float:
    try:
        return float((heur_for_cat or {}).get("delta", 0.0))
    except Exception:
        return 0.0


def _safe_spacy_prob(spacy: Dict[str, float], cat: str):
    if not spacy:
        return None
    try:
        if cat in spacy:
            return _clamp01(float(spacy[cat]))
    except Exception:
        pass
    return None


def compute_score(
    heuristics: Dict[str, Dict[str, Any]],
    llm: Dict[str, Dict[str, Any]],
    spacy: Dict[str, float] = None,
    preference_penalties: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    Blend LLM + heuristics + spaCy + personalized penalties into:
      - per-category scores in [0,1]
      - overall Trust Score (0..100)
      - risk level badge
    """
    per_cat: Dict[str, Dict[str, Any]] = {}
    # Ensure deterministic ordering based on CATEGORY_WEIGHTS
    for cat, weight in CATEGORY_WEIGHTS.items():
        llm_for_cat  = (llm or {}).get(cat) or {}
        heur_for_cat = (heuristics or {}).get(cat) or {}

        llm_score  = _clamp01(_safe_llm_score(llm_for_cat))
        heur_delta = _safe_heur_delta(heur_for_cat)
        spacy_prob = _safe_spacy_prob(spacy or {}, cat)

        # Heuristic-adjusted LLM score (nudged, then clamped)
        llm_plus_heur = _clamp01(llm_score + heur_delta)

        # Core blend (linear, simple & explainable)
        # If spaCy prob is None, its weight is ignored
        if spacy_prob is None:
            blended = ALPHA_LLM * llm_score + BETA_REGEX * llm_plus_heur
        else:
            blended = (
                ALPHA_LLM * llm_score +
                BETA_REGEX * llm_plus_heur +
                GAMMA_SPACY * spacy_prob
            )

        blended = _clamp01(blended)

        # Apply personalized penalty (usually negative) if present
        pen = 0.0
        if preference_penalties and cat in preference_penalties:
            try:
                pen = float(preference_penalties[cat])
            except Exception:
                pen = 0.0

        final_score = _clamp01(blended + pen)

        per_cat[cat] = {
            "score": final_score,
            "reason": _safe_llm_reason(llm_for_cat, heur_for_cat),
            "heuristics": {
                "delta": heur_delta,
                "flags": (heur_for_cat or {}).get("flags") or []
            },
            "spacy_prob": spacy_prob
        }

    # Weighted sum → 0..100
    trust_score = 0.0
    for cat, weight in CATEGORY_WEIGHTS.items():
        trust_score += 100.0 * float(weight) * float(per_cat[cat]["score"])
    trust_score = round(trust_score, 1)

    return {
        "trust_score": trust_score,
        "risk_level": _risk_label(trust_score),
        "categories": per_cat
    }
