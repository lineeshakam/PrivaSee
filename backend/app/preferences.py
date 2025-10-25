# app/preferences.py
from typing import Dict, Any, Tuple

# Simple, front-end-friendly questionnaire.
# True means "I prefer to KEEP this private / I OPT OUT".
PREFERENCE_SCHEMA: Dict[str, Dict[str, Any]] = {
    "protect_location": {
        "type": "boolean",
        "title": "Keep my precise location private",
        "category": "Children/Minors + Sensitive Data",  # also Security/Intl; we’ll map in conflicts
        "default": True
    },
    "opt_out_targeted_ads": {
        "type": "boolean",
        "title": "Opt out of targeted/behavioral advertising",
        "category": "User Control & Rights",
        "default": True
    },
    "no_sale_or_sharing": {
        "type": "boolean",
        "title": "Do not sell or share my personal data",
        "category": "Third-Party Sharing/Selling",
        "default": True
    },
    "limit_data_collection": {
        "type": "boolean",
        "title": "Limit the types of data collected (only necessary)",
        "category": "Data Collection",
        "default": False
    },
    "short_retention": {
        "type": "boolean",
        "title": "Do not retain my data indefinitely (short retention only)",
        "category": "Retention & Deletion",
        "default": True
    },
    "restrict_cross_border": {
        "type": "boolean",
        "title": "Avoid cross-border transfers unless strong safeguards",
        "category": "International Transfers & Jurisdiction",
        "default": False
    },
    "strong_security": {
        "type": "boolean",
        "title": "Require strong security (encryption, access controls, breach notice)",
        "category": "Security Practices",
        "default": True
    },
    "child_privacy": {
        "type": "boolean",
        "title": "Protect minors’ data and sensitive categories",
        "category": "Children/Minors + Sensitive Data",
        "default": True
    },
}

def default_preferences() -> Dict[str, Any]:
    return {k: v["default"] for k, v in PREFERENCE_SCHEMA.items()}

def validate_preferences(prefs: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    if not isinstance(prefs, dict):
        return False, default_preferences()
    cleaned = default_preferences()
    for key, meta in PREFERENCE_SCHEMA.items():
        if key in prefs:
            cleaned[key] = bool(prefs[key])
    return True, cleaned