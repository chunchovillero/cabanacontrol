import json
import logging


class SafeFormatter(logging.Formatter):
    def format(self, record):
        status = getattr(record, "status_code", None)
        return json.dumps(
            {
                "event": "server_error" if record.levelno >= logging.ERROR else "server_notice",
                "level": record.levelname,
                "status": status if isinstance(status, int) else None,
            }
        )
