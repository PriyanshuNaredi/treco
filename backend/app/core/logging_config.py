import json
import logging
import time

from app.core.request_id import request_id_var


class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        req_id = request_id_var.get("")
        if req_id:
            entry["request_id"] = req_id
        if record.exc_info:
            entry["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def configure_logging() -> None:
    formatter = _JSONFormatter()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)

    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        lg = logging.getLogger(name)
        lg.handlers = [handler]
        lg.propagate = False
