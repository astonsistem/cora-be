import logging
import sys

from app.core.config.config import settings

class AppLogging:
    FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    SERVER_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")
    QUIET_LOGGERS = ("httpx", "httpcore")

    @classmethod
    def configure(cls, level: str | None = None) -> None:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(cls.FORMAT, cls.DATE_FORMAT))

        root = logging.getLogger()
        root.handlers = [handler]
        root.setLevel(cls._resolve(level or settings.log_level))

        for name in cls.SERVER_LOGGERS:
            server_logger = logging.getLogger(name)
            server_logger.handlers = []
            server_logger.propagate = True

        for name in cls.QUIET_LOGGERS:
            logging.getLogger(name).setLevel(logging.WARNING)

    @staticmethod
    def _resolve(level: str) -> int:
        resolved = logging.getLevelName(str(level).upper())
        return resolved if isinstance(resolved, int) else logging.INFO
