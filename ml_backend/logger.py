import logging
import logging.handlers
import os
from pathlib import Path


LOGS_DIR = Path(os.environ.get("LOGS_DIR", Path(__file__).parent.parent / "logs"))
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES", 10 * 1024 * 1024))
LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", 5))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()


def _make_rotating_handler(filename: str, level: int = logging.DEBUG) -> logging.handlers.RotatingFileHandler:
    handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / filename,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(_get_formatter())
    return handler


def _get_formatter() -> logging.Formatter:
    return logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _configure_logger(name: str, filename: str, error_filename: str | None = None) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    console_handler.setFormatter(_get_formatter())
    logger.addHandler(console_handler)

    logger.addHandler(_make_rotating_handler(filename))

    if error_filename:
        error_handler = _make_rotating_handler(error_filename, level=logging.ERROR)
        logger.addHandler(error_handler)

    return logger


def get_predict_logger() -> logging.Logger:
    return _configure_logger("ner.predict", "predict.log")


def get_fit_logger() -> logging.Logger:
    return _configure_logger("ner.fit", "fit.log")


def get_webapi_logger() -> logging.Logger:
    return _configure_logger("ner.webapi", "webapi.log", error_filename="webapi_errors.log")


def get_training_logger() -> logging.Logger:
    return _configure_logger("ner.training", "training.log")


def get_app_logger() -> logging.Logger:
    return _configure_logger("ner.app", "app.log", error_filename="app_errors.log")


def get_llm_logger() -> logging.Logger:
    return _configure_logger("ner.llm", "llm.log", error_filename="llm_errors.log")
