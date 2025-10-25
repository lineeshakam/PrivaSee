#hi

from typing import Dict, Any, List
import json
import google.generativeai as genai
from .config import GEMINI_API_KEY, GEMINI_MODEL, CATEGORY_WEIGHTS

# ---- Gemini setup ----
genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel(GEMINI_MODEL)

# ---- Shared helpers ----
def _call_gemini(prompt: str, system: str = None, retries: int = 2) -> str:
    """Robust wrapper that returns plain text; raises last error if all retries fail."""
    for attempt in range(retries + 1):
        try:
            if system:
                # Combine system and user prompt for Gemini
                full_prompt = f"{system}\n\n{prompt}"
                resp = _model.generate_content(full_prompt)
            else:
                resp = _model.generate_content(prompt)
            return resp.text or ""
        except Exception as e:
            if attempt >= retries:
                raise
    return ""

def _safe_json(text: str) -> Any:
    """Extract first JSON object/array from model output and parse it."""
    start = text.find("{")
    if start == -1:
        start = text.find("[")
    if start == -1:
        return {}
    # naive bracket match
    stack = []
    end = start
    for i, ch in enumerate(text[start:], start=start):
        if ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if not stack:
                break
            left = stack.pop()
            if (left, ch) not in {("{","}"), ("[","]")}:
                break
            if not stack:
                end = i + 1
                break
    try:
        return json.loads(text[start:end])
    except Exception:
        return {}

# ============================================================
# 1) GENERAL EVALUATION (for the human-facing “overview” box)
# ============================================================
def llm_general_eval(text: str) -> Dict[str, Any]:
    """
    Returns a concise, structured overview of the policy:
      {
        "overall_rating": 0-100,
        "risk_level": "High|Medium|Low",
        "summary": "2–4 sentence neutral overview",
        "strengths": ["..."],
        "risks": [{"issue":"...", "severity":"low|medium|high"}],
        "missing_disclosures": ["..."],   # important items not stated
        "action_items": ["..."]           # what a user should check/do
      }
    """
    system = (
        "You are a precise privacy-policy analyst. "
        "Be neutral, concise, and evidence-oriented. If information is not stated, say so."
    )
    # Keep rubric simple and consistent with your badge bands (0–39/40–69/70–100)
    prompt = f"""
Read the policy text below and produce ONLY a JSON object with this schema:
{{
  "overall_rating": <integer 0-100>,
  "risk_level": "<High|Medium|Low>",
  "summary": "<2-4 sentences, neutral and concrete>",
  "strengths": ["<short bullet>", "..."],
  "risks": [{{"issue":"<short>", "severity":"<low|medium|high>"}}, ...],
  "missing_disclosures": ["<short item>", "..."],
  "action_items": ["<short, actionable advice>", "..."]
}}
Rules:
- Base "risk_level" on rating: 0–39 = High, 40–69 = Medium, 70–100 = Low.
- If unsure, keep conservative (lower the rating).
- Do NOT include any text outside the JSON.

TEXT:
\"\"\"{text}\"\"\""""

    out = _call_gemini(prompt, system=system)
    data = _safe_json(out)

    # Minimal sanity defaults
    if not isinstance(data, dict):
        data = {}
    data.setdefault("overall_rating", 50)
    data.setdefault("risk_level", "Medium")
    data.setdefault("summary", "No concise summary produced.")
    data.setdefault("strengths", [])
    data.setdefault("risks", [])
    data.setdefault("missing_disclosures", [])
    data.setdefault("action_items", [])
    return data

# ============================================================
# 2) PER-CATEGORY SCORING (the original thing you wanted)
# ============================================================
def llm_summary_categories(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Returns per-category normalized scores in [0,1] + short reasons, exactly for your scorer:
    {
      "Data Collection": {"score": 0.72, "reason": "States categories collected; excludes sensitive data."},
      "Third-Party Sharing/Selling": {"score": 0.25, "reason": "Mentions sharing with partners; no opt-out."},
      ...
    }
    """
    categories = list(CATEGORY_WEIGHTS.keys())

    system = (
        "You are a precise privacy-policy scorer. "
        "Score each category independently in [0,1]. "
        "Use 0 for very poor or absent disclosures; 1 for exemplary clarity, limits, and user rights. "
        "Keep reasons short (<= 25 words)."
    )
    prompt = f"""
Given the privacy policy text, output ONLY a JSON object mapping category -> {{"score": float, "reason": string}}.
- Categories (exact keys): {categories}
- Clamp scores to [0,1].
- Penalize vagueness (e.g., "legitimate interests", "may share", "as long as necessary") without concrete limits.
- Bonus for explicit user rights, retention timelines, encryption, opt-out links, COPPA stance, SCCs/DPF, etc.
- Do NOT include any text outside the JSON.

TEXT:
\"\"\"{text}\"\"\""""

    out = _call_gemini(prompt, system=system)
    data = _safe_json(out)

    # Fill missing categories & clamp
    def _clamp(x): 
        try:
            return max(0.0, min(1.0, float(x)))
        except Exception:
            return 0.5

    clean: Dict[str, Dict[str, Any]] = {}
    for cat in categories:
        entry = data.get(cat, {}) if isinstance(data, dict) else {}
        score = _clamp(entry.get("score", 0.5))
        reason = entry.get("reason", "")
        clean[cat] = {"score": score, "reason": reason[:200]}
    return clean

# ============================================================
# (Optional) One-call convenience that can do both
# ============================================================
def llm_summary(text: str, want_general: bool = False, want_categories: bool = True) -> Dict[str, Any]:
    """
    Convenience wrapper:
      - want_categories=True -> returns per-category scores (original behavior)
      - want_general=True    -> also returns a general 'overview'
    """
    out: Dict[str, Any] = {}
    if want_categories:
        out["categories"] = llm_summary_categories(text)
        # For backward-compat, also surface the flat dict categories->{"score","reason"}
        for k, v in out["categories"].items():
            out[k] = v
    if want_general:
        out["general"] = llm_general_eval(text)
    return out