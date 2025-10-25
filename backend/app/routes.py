# app/routes.py
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest
from . import config
from .heuristics import detect_flags           # expects detect_flags(text) -> {category: {...}}
from .summarizer_gemini import llm_summary     # expects llm_summary(text) -> {category: {"score": float, "reason": str}}
from .scoring import compute_score             # expects compute_score(heur, llm) -> dict payload

bp = Blueprint("api", __name__)

MAX_TEXT_LEN = 120_000  # keep generous for whole-page mode

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
        "include_spacy_probs": true|false,# optional, default true (blend spaCy probs)
        "return_general": true|false      # optional, default true (Gemini overview box)
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
        "overview": {                      # <-- general evaluation from Gemini
          "overall_rating": 64,
          "risk_level": "Medium",
          "summary": "…",
          "strengths": ["…"],
          "risks": [{"issue":"…","severity":"high"}],
          "missing_disclosures": ["…"],
          "action_items": ["…"]
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

    # Options
    return_snippets     = bool(payload.get("return_snippets", True))
    snippets_top_k      = int(payload.get("snippets_top_k", 3))
    include_spacy_probs = bool(payload.get("include_spacy_probs", True))
    return_general      = bool(payload.get("return_general", True))

    # 1) Fast regex heuristics (deterministic flags/bonuses/penalties)
    heur = detect_flags(text)  # expected per-category dict with at least {"delta": float, "flags": [...]}

    # 2) Gemini: per-category scores (for Trust Score) + general overview (for top-card)
    from .summarizer_gemini import llm_summary_categories, llm_general_eval
    llm_cats = llm_summary_categories(text)      # {"Category": {"score": float, "reason": str}, ...}
    llm_overview = llm_general_eval(text) if return_general else None

    # 3) spaCy signals
    spacy_probs = {}
    evidence = {}

    if include_spacy_probs:
        try:
            from .nlp_spacy import spacy_scores
            spacy_probs = spacy_scores(text) or {}
        except Exception:
            spacy_probs = {}

    if return_snippets:
        try:
            from .nlp_spacy import spacy_extract_category_lines
            evidence = spacy_extract_category_lines(text, top_k=snippets_top_k) or {}
        except Exception:
            evidence = {}

    # 4) Combine with weights into a transparent Trust Score (blend LLM + heuristics + spaCy)
    #    compute_score should gracefully handle missing spaCy by ignoring empty dicts.
    result = compute_score(heuristics=heur, llm=llm_cats, spacy=spacy_probs)

    # Attach weights, overview, and (optional) evidence for the UI
    result["weights"] = config.CATEGORY_WEIGHTS
    if return_general and llm_overview:
        result["overview"] = llm_overview
    if return_snippets:
        result["evidence"] = evidence

    return jsonify(result), 200


# Optional: lightweight error mappers for cleaner client messages
@bp.errorhandler(BadRequest)
def handle_bad_request(err):
    return jsonify({"error": "bad_request", "message": err.description}), 400

@bp.errorhandler(Exception)
def handle_uncaught(err):
    # Avoid leaking stack traces to clients during demos; log server-side instead.
    return jsonify({"error": "internal_error", "message": "Unhandled server error."}), 500