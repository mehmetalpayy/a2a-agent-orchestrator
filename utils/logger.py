"""Lightweight logger utilities."""

import logging
import os
from typing import Any


class Logger:
    _logger: logging.Logger | None = None

    @classmethod
    def _create_logger(cls) -> logging.Logger:
        logger = logging.getLogger("a2a_orchestrator")
        if logger.hasHandlers():
            logger.handlers.clear()
        logger.propagate = False

        level_name = os.getenv("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)
        logger.setLevel(level)

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        return logger

    @classmethod
    def get_logger(cls) -> logging.Logger:
        if cls._logger is None:
            cls._logger = cls._create_logger()
        return cls._logger

    @classmethod
    def info(cls, message: str, *args: Any, **kwargs: Any) -> None:
        cls.get_logger().info(message, *args, **kwargs)

    @classmethod
    def warn(cls, message: str, *args: Any, **kwargs: Any) -> None:
        cls.get_logger().warning(message, *args, **kwargs)

    @classmethod
    def error(cls, message: str, *args: Any, **kwargs: Any) -> None:
        cls.get_logger().error(message, *args, **kwargs)

    @classmethod
    def debug(cls, message: str, *args: Any, **kwargs: Any) -> None:
        cls.get_logger().debug(message, *args, **kwargs)

    @classmethod
    def set_logger(cls, logger: logging.Logger) -> None:
        cls._logger = logger


def get_logger() -> logging.Logger:
    return Logger.get_logger()
