# app/routes.py
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest
from . import config
from .heuristics import detect_flags           # expects detect_flags(text) -> {category: {...}}
from .summarizer_gemini import llm_summary     # expects llm_summary(text) -> {category: {"score": float, "reason": str}}
from .scoring import compute_score             # expects compute_score(heur, llm) -> dict payload
from .preferences import validate_preferences, default_preferences, PREFERENCE_SCHEMA
from .policy_conflicts import detect_conflicts
from .nlp_spacy import spacy_extract_category_lines, spacy_scores


bp = Blueprint("api", __name__)

MAX_TEXT_LEN = 120_000  # keep generous for whole-page mode

from flask import current_app
import logging, traceback

@bp.errorhandler(Exception)
def handle_uncaught(err):
    logging.exception(err)  # prints full stack to the server console
    if current_app.debug:
        return jsonify({"error":"internal_error", "message": str(err)}), 500
    return jsonify({"error":"internal_error", "message": "Unhandled server error."}), 500

@bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "api_version": getattr(config, "API_VERSION", "v1"),
        "model": getattr(config, "GEMINI_MODEL", "gemini-1.5-flash")
    }), 200


@bp.route("/analyze", methods=["POST"])
def analyze():
    """
    Request JSON schema:
      {
        "text": "string (required)",
        "mode": "selection" | "page",     # optional, for logging
        "return_snippets": true|false,    # optional, default true (spaCy evidence lines)
        "snippets_top_k": 3,              # optional, default 3
        "include_spacy_probs": true|false # optional, default true (blend spaCy probs)
      }

    Response JSON schema (example):
      {
        "trust_score": 68.4,
        "risk_level": "Medium",
        "categories": {
          "Third-Party Sharing/Selling": {
            "score": 0.32,
            "reason": "Mentions sharing with partners; no opt-out link found.",
            "heuristics": {"delta": -0.35, "flags": ["share with third parties"]},
            "spacy_prob": 0.41
          },
          ...
        },
        "evidence": {
          "Third-Party Sharing/Selling": [
            {"text": "...share with third parties...", "start": 1234, "end": 1298, "score": 0.82, "matched": ["share with third parties"]}
          ],
          ...
        },
        "weights": { "...": 0.10, ... }
      }
    """
    # Content-type guard
    if not request.is_json:
        raise BadRequest("Content-Type must be application/json")

    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    if not text:
        raise BadRequest("Field 'text' is required and must be non-empty.")
    if len(text) > MAX_TEXT_LEN:
        raise BadRequest(f"Text too long (>{MAX_TEXT_LEN} chars). Consider 'selection' mode.")
    # --- Personalized preferences (optional) ---
    ok, prefs = validate_preferences(payload.get("preferences", default_preferences()))

    # Options
    return_snippets = bool(payload.get("return_snippets", True))
    snippets_top_k = int(payload.get("snippets_top_k", 3))
    include_spacy_probs = bool(payload.get("include_spacy_probs", True))

    # 1) Fast regex heuristics (deterministic flags/bonuses/penalties)
    heur = detect_flags(text)  # expected per-category dict with at least {"delta": float, "flags": [...]}

    # 2) Gemini semantic judgments (normalized category scores in [0,1] + short reasons)
    llm = llm_summary(text)    # expected per-category: {"score": float, "reason": str}

    # 3) spaCy signals
    spacy_probs = {}
    evidence = {}

    if include_spacy_probs:
        # Optional numeric per-category probabilities in [0,1] (used by scoring blend)
        try:
            from .nlp_spacy import spacy_scores
            spacy_probs = spacy_scores(text) or {}
        except Exception:
            spacy_probs = {}

    if return_snippets:
        # Sentence-level evidence lines per category (top-K)
        try:
            from .nlp_spacy import spacy_extract_category_lines
            evidence = spacy_extract_category_lines(text, top_k=snippets_top_k) or {}
        except Exception:
            evidence = {}

      # --- Detect conflicts with user preferences before scoring ---
    conflicts = detect_conflicts(prefs, categories={}, evidence=evidence)
    penalties = {}
    for c in conflicts:
        cat = c["category"]
        penalties[cat] = penalties.get(cat, 0.0) - 0.10  # gentle personalized penalty


    # 4) Combine with weights into a transparent Trust Score (blend LLM + heuristics + spaCy)
    #    compute_score should gracefully handle missing spaCy by ignoring empty dicts.
        # Compute with preference penalties
    result = compute_score(heuristics=heur, llm=llm, spacy=spacy_probs, preference_penalties=penalties)

    # Re-run conflict detection now that categories have scores
    conflicts = detect_conflicts(prefs, categories=result["categories"], evidence=evidence)


        # Attach personalized + transparency info
    result["weights"] = config.CATEGORY_WEIGHTS
    result["preferences"] = {"valid": ok, "values": prefs, "schema": PREFERENCE_SCHEMA}
    if return_snippets:
        result["evidence"] = evidence
    result["personalized"] = {"conflicts": conflicts, "penalties": penalties}

    return jsonify(result), 200


# Optional: lightweight error mappers for cleaner client messages
@bp.errorhandler(BadRequest)
def handle_bad_request(err):
    return jsonify({"error": "bad_request", "message": err.description}), 400

@bp.errorhandler(Exception)
def handle_uncaught(err):
    # Avoid leaking stack traces to clients during demos; log server-side instead.
    return jsonify({"error": "internal_error", "message": "Unhandled server error."}), 500