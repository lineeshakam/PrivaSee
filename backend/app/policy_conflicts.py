# app/policy_conflicts.py
from typing import Dict, Any, List

# Map preferences -> which categories & keywords/evidence to watch for
PREF_TO_SIGNALS = {
    "protect_location": {
        "categories": ["Children/Minors + Sensitive Data", "Data Collection"],
        "keywords": ["precise location", "geolocation", "gps", "location data"]
    },
    "opt_out_targeted_ads": {
        "categories": ["User Control & Rights", "Third-Party Sharing/Selling"],
        "keywords": ["behavioral advertising", "targeted ads", "adtech", "cross-site tracking"]
    },
    "no_sale_or_sharing": {
        "categories": ["Third-Party Sharing/Selling"],
        "keywords": ["sell", "sale", "data broker", "share with third"]
    },
    "limit_data_collection": {
        "categories": ["Data Collection", "Purpose Limitation"],
        "keywords": ["categories of information", "collect", "legitimate interests", "compatible further processing"]
    },
    "short_retention": {
        "categories": ["Retention & Deletion"],
        "keywords": ["retain indefinitely", "as long as necessary", "retention period"]
    },
    "restrict_cross_border": {
        "categories": ["International Transfers & Jurisdiction"],
        "keywords": ["international transfers", "cross-border", "standard contractual clauses", "adequacy decision"]
    },
    "strong_security": {
        "categories": ["Security Practices"],
        "keywords": ["encryption", "TLS", "access controls", "breach notification", "ISO 27001", "SOC 2"]
    },
    "child_privacy": {
        "categories": ["Children/Minors + Sensitive Data"],
        "keywords": ["coppa", "children", "minor", "biometric", "health data", "sensitive categories"]
    },
}

def _text_contains_any(s: str, terms: List[str]) -> bool:
    s_low = s.lower()
    return any(t in s_low for t in terms)

def detect_conflicts(
    preferences: Dict[str, bool],
    categories: Dict[str, Dict[str, Any]],
    evidence: Dict[str, List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """
    preferences: validated prefs
    categories: result["categories"] from scoring (per-category score + reason + heuristics)
    evidence: spacy evidence lines per category (as returned by spacy_extract_category_lines)
    Returns list of conflict dicts with helpful messages and pointers to evidence.
    """
    conflicts = []
    for pref_key, enabled in preferences.items():
        if not enabled:
            continue
        spec = PREF_TO_SIGNALS.get(pref_key)
        if not spec:
            continue

        hit_any = False
        matched_cat = None
        matched_ev = None

        # Scan categories & evidence for problematic signals
        for cat in spec["categories"]:
            ev_list = evidence.get(cat, []) or []
            # Prefer an evidence line that includes one of the keywords
            for ev in ev_list:
                if _text_contains_any(ev["text"], spec["keywords"]):
                    hit_any = True
                    matched_cat = cat
                    matched_ev = ev
                    break
            if hit_any:
                break

            # Fallback: if category score is notably low, consider it a potential conflict
            cat_score = (categories.get(cat) or {}).get("score", 1.0)
            if cat_score <= 0.35 and ev_list:
                hit_any = True
                matched_cat = cat
                matched_ev = ev_list[0]

        if hit_any and matched_cat:
            conflicts.append({
                "preference": pref_key,
                "category": matched_cat,
                "message": _human_message(pref_key, matched_cat, matched_ev),
                "evidence": matched_ev
            })
    return conflicts

def _human_message(pref_key: str, category: str, ev: Dict[str, Any]) -> str:
    # Friendly, demo-ready sentences
    templates = {
        "protect_location": "This app references collecting or sharing precise location, which conflicts with your preference to keep location private.",
        "opt_out_targeted_ads": "This policy mentions behavioral/targeted advertising; you prefer to opt out of that.",
        "no_sale_or_sharing": "We found language about selling or sharing personal data; you opted to avoid sale/sharing.",
        "limit_data_collection": "They describe broad collection or vague purposes; you prefer limiting data collection.",
        "short_retention": "They imply long/indefinite retention; you prefer short retention periods.",
        "restrict_cross_border": "Cross-border transfers are mentioned; you prefer restricting transfers without strong safeguards.",
        "strong_security": "Security language appears weak or absent; you prefer strong security practices.",
        "child_privacy": "Children/sensitive data handling may be insufficient; you prefer stricter protection.",
    }
    base = templates.get(pref_key, "This seems to conflict with your stated preference.")
    snippet = (ev or {}).get("text", "")
    return f"{base} Example: “{snippet}”"
