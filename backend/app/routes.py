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
        "mode": "selection" | "page"  # optional, for logging/telemetry if you want
      }

    Response JSON schema (example):
      {
        "trust_score": 68.4,
        "risk_level": "Medium",
        "categories": {
          "Third-Party Sharing/Selling": {
            "score": 0.32,
            "reason": "Mentions sharing with partners; no opt-out link found.",
            "heuristics": {"flags": ["share with third parties"], "deltas": -0.35}
          },
          ...
        }
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

    # 1) Fast regex heuristics (deterministic flags/bonuses/penalties)
    heur = detect_flags(text)  # your function should return per-category info

    # 2) Gemini semantic judgments (normalized category scores in [0,1] + short reasons)
    llm = llm_summary(text)    # your function returns per-category {score, reason}

    # 3) Combine with weights into a transparent Trust Score
    result = compute_score(heur, llm)  # returns final JSON-serializable dict

    # Optional: include the configured weights once for transparency
    result["weights"] = config.CATEGORY_WEIGHTS

    return jsonify(result), 200


# Optional: lightweight error mappers for cleaner client messages
@bp.errorhandler(BadRequest)
def handle_bad_request(err):
    return jsonify({"error": "bad_request", "message": err.description}), 400

@bp.errorhandler(Exception)
def handle_uncaught(err):
    # Avoid leaking stack traces to clients during demos; log server-side instead.
    return jsonify({"error": "internal_error", "message": "Unhandled server error."}), 500