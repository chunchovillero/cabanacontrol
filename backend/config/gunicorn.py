logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"safe": {"()": "config.production_logging.SafeFormatter"}},
    "handlers": {"safe": {"class": "logging.StreamHandler", "formatter": "safe"}},
    "root": {"handlers": ["safe"], "level": "WARNING"},
    "loggers": {
        "gunicorn.error": {"handlers": ["safe"], "level": "INFO", "propagate": False},
        "gunicorn.access": {"handlers": ["safe"], "level": "WARNING", "propagate": False},
    },
}
secure_scheme_headers = {"X-FORWARDED-PROTO": "https"}
accesslog = None
