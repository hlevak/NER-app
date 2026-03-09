import os
from pathlib import Path

from dotenv import load_dotenv

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
    logger.info("ML Backend application created successfully")
    return app


app = create_app()

if __name__ == "__main__":
    host = os.environ.get("ML_BACKEND_HOST", "0.0.0.0")
    port = int(os.environ.get("ML_BACKEND_PORT", "9090"))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    logger.info("Starting ML Backend on %s:%d (debug=%s)", host, port, debug)
    app.run(host=host, port=port, debug=debug)
