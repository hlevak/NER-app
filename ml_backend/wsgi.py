import os
from pathlib import Path

from dotenv import load_dotenv
from flask import request, jsonify

_env_path = Path(__file__).parent.parent / "config" / "ml-backend.env"
if _env_path.exists():
    load_dotenv(_env_path)

from label_studio_ml.api import init_app
from .combined_ner_backend import CombinedNERBackend
from .logger import get_app_logger

logger = get_app_logger()


def create_app():
    logger.info("Creating ML Backend Flask application")
    app = init_app(model_class=CombinedNERBackend)

    @app.route("/suggestions", methods=["POST"])
    def suggestions():
        """Get entity suggestions for autocomplete."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        text = data.get("text", "")
        partial = data.get("partial", "")
        context = data.get("context", "")

        if not text or not partial:
            return jsonify({"error": "Missing required fields: text, partial"}), 400

        try:
            model = app.model
            suggestions_list = model.get_suggestions(text, partial, context)
            return jsonify({"suggestions": suggestions_list})
        except Exception as exc:
            logger.error("Suggestions endpoint error: %s", exc)
            return jsonify({"error": str(exc)}), 500

    @app.route("/normalize", methods=["POST"])
    def normalize():
        """Normalize/verify an entity."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        text = data.get("text", "")
        label = data.get("label", "")

        if not text or not label:
            return jsonify({"error": "Missing required fields: text, label"}), 400

        try:
            model = app.model
            result = model.normalize_entity(text, label)
            return jsonify(result)
        except Exception as exc:
            logger.error("Normalize endpoint error: %s", exc)
            return jsonify({"error": str(exc)}), 500

    @app.route("/health", methods=["GET"])
    def health():
        """Health check endpoint."""
        try:
            model = app.model
            return jsonify({
                "status": "ok",
                "webapi_configured": model.webapi_client.is_configured(),
                "llm_configured": model.llm_client.is_configured(),
            })
        except Exception as exc:
            return jsonify({"status": "error", "error": str(exc)}), 500

    @app.route("/interactive", methods=["POST"])
    def interactive():
        """Interactive mode for real-time predictions during annotation.
        
        Label Studio calls this endpoint when user is actively editing
        to provide immediate feedback and suggestions.
        """
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        try:
            model = app.model
            result = model.interactive_annotate(data)
            return jsonify(result)
        except Exception as exc:
            logger.error("Interactive endpoint error: %s", exc)
            return jsonify({"error": str(exc)}), 500

    @app.route("/setup", methods=["POST"])
    def setup():
        """Setup endpoint called by Label Studio when connecting ML Backend.
        
        Returns configuration info for the ML Backend.
        """
        try:
            model = app.model
            return jsonify({
                "status": "ok",
                "model_class": "CombinedNERBackend",
                "supported_modes": ["pre-annotation", "interactive", "training"],
                "capabilities": {
                    "predict": True,
                    "fit": True,
                    "interactive": True,
                    "suggestions": True,
                },
                "webapi_configured": model.webapi_client.is_configured(),
                "llm_configured": model.llm_client.is_configured(),
            })
        except Exception as exc:
            logger.error("Setup endpoint error: %s", exc)
            return jsonify({"status": "error", "error": str(exc)}), 500

    logger.info("ML Backend application created successfully")
    return app


app = create_app()

if __name__ == "__main__":
    host = os.environ.get("ML_BACKEND_HOST", "0.0.0.0")
    port = int(os.environ.get("ML_BACKEND_PORT", "9090"))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    logger.info("Starting ML Backend on %s:%d (debug=%s)", host, port, debug)
    app.run(host=host, port=port, debug=debug)
