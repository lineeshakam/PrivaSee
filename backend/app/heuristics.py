from __future__ import annotations
import re
from typing import Dict, List, Tuple
from .config import CATEGORY_WEIGHTS

# -------- helpers --------

def _rx(pattern: str, flags=re.IGNORECASE | re.MULTILINE) -> re.Pattern:
    return re.compile(pattern, flags)

def _count(pattern: re.Pattern, text: str) -> int:
    return sum(1 for _ in pattern.finditer(text))

def _apply(delta: float, amount: float) -> float:
    return max(-1.0, min(1.0, delta + amount))

# -------- patterns (penalties / bonuses) --------

PATTERNS = {
    # --- Third-Party Sharing/Selling ---
    "TP_SELL": {
        "cat": "Third-Party Sharing/Selling",
        "regex": _rx(r"\b(sell|sale|sold|monetiz(?:e|ation)|broker|data broker)\b"),
        "delta": -0.35,
        "flag": "Mentions selling/monetizing or broker relationship",
        "type": "penalty"
    },
    "TP_SHARE_THIRDPARTY": {
        "cat": "Third-Party Sharing/Selling",
        "regex": _rx(r"\bshare(?:s|d|ing)?\b.{0,30}\b(third[- ]?part(?:y|ies)|partners?)\b"),
        "delta": -0.25,
        "flag": "Mentions sharing with third parties/partners",
        "type": "penalty"
    },
    "TP_DNS_LINK": {
        "cat": "User Control & Rights",  # UI control but helps Sharing via user choice
        "regex": _rx(r"do\s+not\s+(sell|share)", re.IGNORECASE),
        "delta": +0.15,
        "flag": "Provides a Do Not Sell/Share option",
        "type": "bonus"
    },

    # --- Tracking/Ads (affects Sharing & Purpose Limitation slightly) ---
    "ADS_TRACKING": {
        "cat": "Third-Party Sharing/Selling",
        "regex": _rx(r"\b(adtech|behavioral\s+advertising|targeted\s+ads|cross[- ]site\s+tracking)\b"),
        "delta": -0.15,
        "flag": "Behavioral/targeted advertising or cross-site tracking",
        "type": "penalty"
    },

    # --- Purpose Limitation / Vagueness ---
    "PURPOSE_VAGUE_LI": {
        "cat": "Purpose Limitation",
        "regex": _rx(r"\blegitimate\s+interests\b"),
        "delta": -0.15,
        "flag": "Relies on vague 'legitimate interests'",
        "type": "penalty"
    },
    "PURPOSE_VAGUE_MAY_SHARE": {
        "cat": "Purpose Limitation",
        "regex": _rx(r"\bmay\b.{0,20}\bshare\b"),
        "delta": -0.10,
        "flag": "Vague 'may share' without specifics",
        "type": "penalty"
    },
    "PURPOSE_LIMIT_GOOD": {
        "cat": "Purpose Limitation",
        "regex": _rx(r"\buse(?:d)?\s+only\s+for\b|\bfor\s+the\s+purposes\s+described\b"),
        "delta": +0.10,
        "flag": "States use limited to specific purposes",
        "type": "bonus"
    },

    # --- Data Collection ---
    "COLLECT_SENSITIVE": {
        "cat": "Data Collection",
        "regex": _rx(r"\b(sensitive\s+(personal\s+)?information|biometric|genetic|health\s+data|precise\s+location)\b"),
        "delta": -0.20,
        "flag": "Collects sensitive categories",
        "type": "penalty"
    },
    "COLLECT_LISTS_CATEGORIES": {
        "cat": "Data Collection",
        "regex": _rx(r"\b(categories|types)\s+of\s+(personal\s+)?(information|data)\b"),
        "delta": +0.10,
        "flag": "Discloses categories of data collected",
        "type": "bonus"
    },

    # --- User Rights & Controls ---
    "RIGHTS_LIST": {
        "cat": "User Control & Rights",
        "regex": _rx(r"\b(access|delete|erasure|correct|rectify|portability|opt[- ]?out)\b"),
        "delta": +0.15,
        "flag": "Lists user rights (access/delete/correct/portability/opt-out)",
        "type": "bonus"
    },
    "REGULATORY_RIGHTS": {
        "cat": "User Control & Rights",
        "regex": _rx(r"\b(CCPA|GDPR|Do\s+Not\s+Sell|Do\s+Not\s+Share)\b"),
        "delta": +0.10,
        "flag": "References CCPA/GDPR or Do Not Sell/Share",
        "type": "bonus"
    },

    # --- Retention & Deletion ---
    "RETENTION_INDEFINITE": {
        "cat": "Retention & Deletion",
        "regex": _rx(r"\bretain(?:ed|tion)?\b.*\bindefinite(?:ly)?\b"),
        "delta": -0.25,
        "flag": "States indefinite retention",
        "type": "penalty"
    },
    "RETENTION_VAGUE_LONG": {
        "cat": "Retention & Deletion",
        "regex": _rx(r"\bretain\b.*\b(as long as (?:necessary|needed))\b"),
        "delta": -0.15,
        "flag": "Vague retention ('as long as necessary')",
        "type": "penalty"
    },
    "RETENTION_TIMELINE": {
        "cat": "Retention & Deletion",
        "regex": _rx(r"\b(retention\s+period|deleted\s+after|deletion\s+timeline|retain(?:ed|tion)?\s+for\s+\d+\s+(?:days|months|years))\b"),
        "delta": +0.15,
        "flag": "Provides retention/deletion timelines",
        "type": "bonus"
    },

    # --- Security Practices ---
    "SECURITY_ENCRYPTION": {
        "cat": "Security Practices",
        "regex": _rx(r"\b(encrypt(?:ed|ion)|TLS|HTTPS)\b"),
        "delta": +0.10,
        "flag": "Mentions encryption/TLS",
        "type": "bonus"
    },
    "SECURITY_CONTROLS": {
        "cat": "Security Practices",
        "regex": _rx(r"\b(access\s+controls|SOC\s*2|ISO\s*27001|security\s+measures|breach\s+notification)\b"),
        "delta": +0.10,
        "flag": "Mentions recognized security controls or breach notice",
        "type": "bonus"
    },

    # --- International Transfers & Jurisdiction ---
    "XFER_SAFEGUARDS": {
        "cat": "International Transfers & Jurisdiction",
        "regex": _rx(r"\b(standard\s+contractual\s+clauses|SCCs?|data\s+privacy\s+framework|adequacy\s+decision)\b"),
        "delta": +0.10,
        "flag": "Mentions SCCs/DPF/adequacy safeguards",
        "type": "bonus"
    },
    "JURIS_ARBITRATION": {
        "cat": "International Transfers & Jurisdiction",
        "regex": _rx(r"\b(arbitration|venue|governing\s+law|jurisdiction)\b"),
        "delta": -0.05,
        "flag": "Specifies venue/arbitration (potentially user-unfriendly)",
        "type": "penalty"
    },

    # --- Children & Sensitive Data ---
    "COPPA_CHILDREN": {
        "cat": "Children/Minors + Sensitive Data",
        "regex": _rx(r"\b(COPPA|child(?:ren)?|minor|under\s*1[3-8])\b"),
        "delta": +0.10,
        "flag": "States minors/COPPA stance",
        "type": "bonus"
    },
    "SENSITIVE_LIMITS": {
        "cat": "Children/Minors + Sensitive Data",
        "regex": _rx(r"\b(biometric|health\s+data|precise\s+location)\b.*\b(not\s+collect|do\s+not\s+collect|prohibit)\b"),
        "delta": +0.10,
        "flag": "Limits collection of sensitive categories",
        "type": "bonus"
    },
}

# Some patterns conceptually affect multiple areas; optionally mirror small spillover bonuses/penalties here if you want.

# -------- main API --------

def detect_flags(text: str) -> Dict[str, Dict]:
    """
    Run all regexes and aggregate penalties/bonuses per category.
    Returns a dict keyed by category with delta, flags, and raw hit counts.
    """
    # Initialize per-category buckets
    out: Dict[str, Dict] = {
        cat: {"delta": 0.0, "flags": [], "hits": {}}
        for cat in CATEGORY_WEIGHTS.keys()
    }

    # Apply each pattern; scale deltas by count with mild diminishing return
    for key, spec in PATTERNS.items():
        cat = spec["cat"]
        pat = spec["regex"]
        dlt = float(spec["delta"])
        flag = spec["flag"]
        n = _count(pat, text)

        if n <= 0:
            continue

        # Diminishing returns: effective_count = 1 + 0.5*(n-1) up to 3 hits
        eff = 1.0 + 0.5 * (min(n, 3) - 1.0)
        delta_add = dlt * eff

        out[cat]["delta"] = _apply(out[cat]["delta"], delta_add)
        out[cat]["hits"][key] = n

        # Add a single flag line with count
        pretty = f"{flag} (x{n})" if n > 1 else flag
        out[cat]["flags"].append(pretty)

    return out