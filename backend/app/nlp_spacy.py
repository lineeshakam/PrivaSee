from typing import Dict, List, Any
import os
import spacy
from spacy.matcher import Matcher, PhraseMatcher

CATEGORIES = [
    "Data Collection",
    "Third-Party Sharing/Selling",
    "Purpose Limitation",
    "User Control & Rights",
    "Retention & Deletion",
    "Security Practices",
    "International Transfers & Jurisdiction",
    "Children/Minors + Sensitive Data",
]

# If you train a custom spaCy model with textcat, point SPACY_MODEL_DIR to it
_SPACY_MODEL = os.environ.get("SPACY_MODEL_DIR")
_nlp = None
_MATCHER = None
_PHRASE = None

def _get_nlp():
    global _nlp
    if _nlp is not None:
        return _nlp
    if _SPACY_MODEL and os.path.isdir(_SPACY_MODEL):
        _nlp = spacy.load(_SPACY_MODEL)
    else:
        _nlp = spacy.load("en_core_web_sm")
    if "sentencizer" not in _nlp.pipe_names:
        _nlp.add_pipe("sentencizer")
    return _nlp

def _build_matchers(nlp):
    m = Matcher(nlp.vocab)
    p = PhraseMatcher(nlp.vocab, attr="LOWER")

    # --- Data Collection ---
    p.add("DATA_COLLECTION", [nlp.make_doc(t) for t in [
        "information we collect", "data we collect", "categories of information",
        "collect personal information", "collection of personal data", "sensitive information"
    ]])
    m.add("DATA_COLLECTION_VERB", [[{"LEMMA": "collect"}]])

    # --- Third-Party Sharing/Selling ---
    p.add("THIRDPARTY_PHRASES", [nlp.make_doc(t) for t in [
        "share with third party", "shared with third parties", "our partners", "data broker",
        "sell personal data", "sale of personal data", "monetize data"
    ]])
    m.add("SELL_SHARE", [
        [{"LOWER": {"IN": ["sell","sale","sold","monetize","monetised","monetized","broker"]}}],
        [{"LEMMA": "share"}, {"LOWER": "with"}, {"LOWER": {"IN": ["third","partners","partner","third-party","third-parties"]}}]
    ])

    # --- Purpose Limitation ---
    p.add("PURPOSE_LIMIT", [nlp.make_doc(t) for t in [
        "purpose", "compatible further processing", "use only for", "use for the purposes described"
    ]])
    m.add("VAGUE_BASIS", [[{"LOWER": "legitimate"}, {"LOWER": "interests"}]])

    # --- User Control & Rights ---
    p.add("USER_RIGHTS", [nlp.make_doc(t) for t in [
        "access your data", "delete your data", "erasure", "correct your data", "rectify",
        "data portability", "opt out", "do not sell", "do not share", "ccpa", "gdpr"
    ]])

    # --- Retention & Deletion ---
    p.add("RETENTION", [nlp.make_doc(t) for t in [
        "retain data", "retention period", "deleted after", "deletion timeline", "retain indefinitely",
        "as long as necessary", "as long as needed"
    ]])

    # --- Security Practices ---
    p.add("SECURITY", [nlp.make_doc(t) for t in [
        "encryption", "encrypted", "tls", "iso 27001", "soc 2", "access controls", "security measures",
        "security breach", "breach notification"
    ]])

    # --- International Transfers & Jurisdiction ---
    p.add("INTL", [nlp.make_doc(t) for t in [
        "international transfers", "cross-border", "transfer outside", "jurisdiction", "venue",
        "arbitration", "data privacy framework", "standard contractual clauses", "adequacy decision"
    ]])

    # --- Children/Minors + Sensitive Data ---
    p.add("CHILDREN", [nlp.make_doc(t) for t in [
        "coppa", "child", "children", "minor", "under 13", "under thirteen",
        "biometric", "health data", "precise location", "sensitive categories"
    ]])

    return m, p

def _get_matchers(nlp):
    global _MATCHER, _PHRASE
    if _MATCHER is None or _PHRASE is None:
        _MATCHER, _PHRASE = _build_matchers(nlp)
    return _MATCHER, _PHRASE

PATTERN_TO_CATS = {
    "DATA_COLLECTION": ["Data Collection"],
    "DATA_COLLECTION_VERB": ["Data Collection"],
    "THIRDPARTY_PHRASES": ["Third-Party Sharing/Selling"],
    "SELL_SHARE": ["Third-Party Sharing/Selling"],
    "PURPOSE_LIMIT": ["Purpose Limitation"],
    "VAGUE_BASIS": ["Purpose Limitation"],
    "USER_RIGHTS": ["User Control & Rights"],
    "RETENTION": ["Retention & Deletion"],
    "SECURITY": ["Security Practices"],
    "INTL": ["International Transfers & Jurisdiction"],
    "CHILDREN": ["Children/Minors + Sensitive Data"],
}

def _keyword_hits_to_scores(keyword_hits: Dict[str, int]) -> Dict[str, float]:
    """
    Turn raw hit counts into [0,1] per category. Simple normalization:
      per-pattern contribution = min(1.0, hits/3), summed over patterns then clipped to 1.0.
    """
    out = {cat: 0.0 for cat in CATEGORIES}
    for pat, n in keyword_hits.items():
        cats = PATTERN_TO_CATS.get(pat, [])
        contrib = min(1.0, n / 3.0)
        for c in cats:
            out[c] = min(1.0, out[c] + contrib)
    return out

# ---------------------------
# Public: snippets extractor
# ---------------------------
def spacy_extract_category_lines(text: str, top_k: int = 3, use_textcat: bool = True) -> Dict[str, List[Dict[str, Any]]]:
    """
    For each category, return up to top_k sentence snippets with:
      { "text", "start", "end", "score", "matched": [...] }
    Score blends keyword strength and (if available) textcat confidence.
    """
    nlp = _get_nlp()
    matcher, phr = _get_matchers(nlp)
    doc = nlp(text)

    # If your model has a textcat (doc-level), we’ll reuse doc.cats for each sentence
    has_textcat = use_textcat and any("textcat" in name for name in nlp.pipe_names)
    doc_level_cats = doc.cats if has_textcat else {}

    cat_buckets: Dict[str, List[Dict[str, Any]]] = {c: [] for c in CATEGORIES}

    for sent in doc.sents:
        span = doc[sent.start:sent.end]

        m_hits = matcher(span)
        p_hits = phr(span)

        # Count hits per pattern + collect matched terms
        pat_counts: Dict[str, int] = {}
        matched_terms: List[str] = []
        for match_id, s, e in m_hits:
            name = nlp.vocab.strings[match_id]
            pat_counts[name] = pat_counts.get(name, 0) + 1
            matched_terms.append(span[s:e].text)
        for match_id, s, e in p_hits:
            name = nlp.vocab.strings[match_id]
            pat_counts[name] = pat_counts.get(name, 0) + 1
            matched_terms.append(span[s:e].text)

        if not pat_counts:
            continue

        kw_scores = _keyword_hits_to_scores(pat_counts)

        for cat in CATEGORIES:
            kw = kw_scores.get(cat, 0.0)
            # Blend with any doc-level textcat prob (if available)
            tc = float(doc_level_cats.get(cat, 0.0)) if doc_level_cats else None
            score = 0.7 * kw + (0.3 * tc if tc is not None else 0.0)

            if kw > 0 or (tc is not None and tc > 0.3):
                cat_buckets[cat].append({
                    "text": sent.text.strip(),
                    "start": sent.start_char,
                    "end": sent.end_char,
                    "score": min(1.0, score),
                    "matched": sorted(set(matched_terms)),
                })

    # keep best top_k per category
    for cat in CATEGORIES:
        cat_buckets[cat].sort(key=lambda x: x["score"], reverse=True)
        if top_k is not None:
            cat_buckets[cat] = cat_buckets[cat][:top_k]

    return cat_buckets

# ---------------------------
# Public: per-category probs
# ---------------------------
def spacy_scores(text: str) -> Dict[str, float]:
    """
    Return per-category probabilities in [0,1].
    If a textcat component with matching labels exists, use doc.cats.
    Otherwise, derive a heuristic probability from keyword hits across the whole text.
    """
    nlp = _get_nlp()
    matcher, phr = _get_matchers(nlp)
    doc = nlp(text)

    # If we have a classifier with the right labels, use it.
    if any("textcat" in name for name in nlp.pipe_names) and doc.cats:
        # Ensure only the categories we care about
        return {cat: float(doc.cats.get(cat, 0.0)) for cat in CATEGORIES}

    # Fallback: compute from keyword hits over entire doc
    pat_counts: Dict[str, int] = {}

    # Run on the whole doc once (PhraseMatcher supports full doc too)
    for match_id, s, e in matcher(doc):
        name = nlp.vocab.strings[match_id]
        pat_counts[name] = pat_counts.get(name, 0) + 1
    for match_id, s, e in phr(doc):
        name = nlp.vocab.strings[match_id]
        pat_counts[name] = pat_counts.get(name, 0) + 1

    return _keyword_hits_to_scores(pat_counts)