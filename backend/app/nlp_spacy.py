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
    "Children/Minors + Sensitive Data"
]

# Load spaCy (small model = fast). If you trained a classifier, load that directory instead.
_SPACY_MODEL = os.environ.get("SPACY_MODEL_DIR")  # optional
_nlp = None

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

    # === Keyword / pattern seeds per category (expand as needed) ===
    # Data Collection
    p.add("DATA_COLLECTION", [nlp.make_doc(t) for t in [
        "information we collect", "data we collect", "categories of information",
        "collect personal information", "collection of personal data", "sensitive information"
    ]])
    m.add("DATA_COLLECTION_VERB", [[{"LEMMA": "collect"}]])

    # Third-Party Sharing/Selling
    p.add("THIRDPARTY_PHRASES", [nlp.make_doc(t) for t in [
        "share with third party", "shared with third parties", "our partners", "data broker",
        "sell personal data", "sale of personal data", "monetize data"
    ]])
    m.add("SELL_SHARE", [
        [{"LOWER": {"IN": ["sell","sale","sold","monetize","monetised","monetized","broker"]}}],
        [{"LEMMA": "share"}, {"LOWER": "with"}, {"LOWER": {"IN": ["third","partners","partner","third-party","third-parties"]}}]
    ])

    # Purpose Limitation
    p.add("PURPOSE_LIMIT", [nlp.make_doc(t) for t in [
        "purpose", "compatible further processing", "use only for", "use for the purposes described"
    ]])
    m.add("VAGUE_BASIS", [[{"LOWER": "legitimate"}, {"LOWER": "interests"}]])

    # User Control & Rights
    p.add("USER_RIGHTS", [nlp.make_doc(t) for t in [
        "access your data", "delete your data", "erasure", "correct your data", "rectify",
        "data portability", "opt out", "do not sell", "do not share", "ccpa", "gdpr"
    ]])

    # Retention & Deletion
    p.add("RETENTION", [nlp.make_doc(t) for t in [
        "retain data", "retention period", "deleted after", "deletion timeline", "retain indefinitely",
        "as long as necessary", "as long as needed"
    ]])

    # Security Practices
    p.add("SECURITY", [nlp.make_doc(t) for t in [
        "encryption", "encrypted", "tls", "iso 27001", "soc 2", "access controls", "security measures",
        "security breach", "breach notification"
    ]])

    # International Transfers & Jurisdiction
    p.add("INTL", [nlp.make_doc(t) for t in [
        "international transfers", "cross-border", "transfer outside", "jurisdiction", "venue",
        "arbitration", "data privacy framework", "standard contractual clauses", "adequacy decision"
    ]])

    # Children/Minors + Sensitive Data
    p.add("CHILDREN", [nlp.make_doc(t) for t in [
        "coppa", "child", "children", "minor", "under 13", "under thirteen",
        "biometric", "health data", "precise location", "sensitive categories"
    ]])

    return m, p

_MATCHER = None
_PHRASE = None
def _get_matchers(nlp):
    global _MATCHER, _PHRASE
    if _MATCHER is None or _PHRASE is None:
        _MATCHER, _PHRASE = _build_matchers(nlp)
    return _MATCHER, _PHRASE

# Optional: name each Matcher/PhraseMatcher pattern to categories
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
    Convert raw hit counts to [0,1] per category. Simple normalization:
    score = min(1.0, hits / 3). Feel free to tune.
    """
    out = {cat: 0.0 for cat in CATEGORIES}
    for pat, n in keyword_hits.items():
        cats = PATTERN_TO_CATS.get(pat, [])
        for c in cats:
            out[c] = min(1.0, out[c] + min(1.0, n / 3.0))
    return out

def spacy_extract_category_lines(text: str, top_k: int = 3, use_textcat: bool = True) -> Dict[str, List[Dict[str, Any]]]:
    """
    Returns, for each category, a list of up to top_k evidence dicts:
      {
        "text": sentence_text,
        "start": char_start,
        "end": char_end,
        "score": float in [0,1],   # blend of keyword strength & (optional) textcat prob
        "matched": ["terms", ...]  # matched keywords (for bolding in UI)
      }
    """
    nlp = _get_nlp()
    matcher, phr = _get_matchers(nlp)
    doc = nlp(text)

    # Precompute classifier probs per sentence (optional)
    sent_textcat = {}
    has_textcat = use_textcat and any(pipe for pipe in nlp.pipe_names if "textcat" in pipe or "textcat_multilabel" in pipe)
    for sent in doc.sents:
        cats = getattr(sent.doc, "cats", None) if has_textcat else None
        # If your classifier is per-doc, you can just reuse doc.cats for all sentences.
        # For per-sentence classification, you'd need a separate nlp on str(sent) (slower).
        sent_textcat[sent.start_char] = cats or {}

    # Collect matches per sentence
    cat_buckets: Dict[str, List[Dict[str, Any]]] = {c: [] for c in CATEGORIES}

    for sent in doc.sents:
        span_doc = doc[sent.start:sent.end]
        # Matcher (token patterns)
        m_hits = matcher(span_doc)
        # PhraseMatcher (lexical phrases)
        p_hits = phr(span_doc)

        # Count hits per pattern and collect matched strings
        pat_counts: Dict[str, int] = {}
        matched_terms: List[str] = []

        for match_id, start, end in m_hits:
            name = nlp.vocab.strings[match_id]
            pat_counts[name] = pat_counts.get(name, 0) + 1
            matched_terms.append(span_doc[start:end].text)

        for match_id, start, end in p_hits:
            name = nlp.vocab.strings[match_id]
            pat_counts[name] = pat_counts.get(name, 0) + 1
            matched_terms.append(span_doc[start:end].text)

        if not pat_counts:
            continue  # no signals in this sentence

        # Convert keyword hits to rough category scores
        kw_scores = _keyword_hits_to_scores(pat_counts)

        # Optional: blend with textcat probabilities if available
        cats = sent_textcat.get(sent.start_char, {}) or {}
        for cat in CATEGORIES:
            kw = kw_scores.get(cat, 0.0)
            tc = float(cats.get(cat, 0.0)) if cats and (cat in cats) else None
            # Blend (simple): score = 0.7*kw + 0.3*tc if tc exists, else kw
            score = 0.7 * kw + (0.3 * tc if tc is not None else 0.0)

            if kw > 0 or (tc is not None and tc > 0.3):
                cat_buckets[cat].append({
                    "text": sent.text.strip(),
                    "start": sent.start_char,
                    "end": sent.end_char,
                    "score": min(1.0, score),
                    "matched": sorted(set(matched_terms))
                })

    # Keep top-k per category by score, stable order for ties
    for cat in CATEGORIES:
        cat_buckets[cat].sort(key=lambda x: x["score"], reverse=True)
        if top_k is not None:
            cat_buckets[cat] = cat_buckets[cat][:top_k]

    return cat_buckets