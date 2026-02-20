import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from app.config.controls import get_controls_value


class _LoggerWriter:
    def __init__(self, logger: logging.Logger, level: int):
        self.logger = logger
        self.level = level
        self._buf = ""

    def write(self, message: str):
        if not message:
            return
        self._buf += message
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            line = line.strip()
            if line:
                self.logger.log(self.level, line)

    def flush(self):
        if self._buf.strip():
            self.logger.log(self.level, self._buf.strip())
        self._buf = ""


def setup_logging() -> logging.Logger:
    path = str(get_controls_value("logging.path", "logs/endpoint.log"))
    max_bytes = int(get_controls_value("logging.max_bytes", 1024 * 1024 * 1024))  # 1GB
    backup_count = int(get_controls_value("logging.backup_count", 1))

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    logger = logging.getLogger("music-studio-control")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")

    file_handler = RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backup_count)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.__stdout__)
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    # capture print() and uncaught writes into logger so we keep detailed history.
    sys.stdout = _LoggerWriter(logger, logging.INFO)
    sys.stderr = _LoggerWriter(logger, logging.ERROR)

    logger.info("logging initialized path=%s max_bytes=%s backup_count=%s", path, max_bytes, backup_count)
    return logger
