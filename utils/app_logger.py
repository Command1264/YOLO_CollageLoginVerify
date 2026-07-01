import io
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path

from utils.app_paths import get_logs_dir


class StreamToLogger(io.TextIOBase):
    def __init__(self, logger: logging.Logger, level: int) -> None:
        super().__init__()
        self.logger = logger
        self.level = level
        self._buffer = ""

    def write(self, text: str) -> int:
        if text is None:
            return 0
        self._buffer += str(text)
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.rstrip("\r")
            if line:
                self.logger.log(self.level, line)
        return len(text)

    def flush(self) -> None:
        line = self._buffer.strip()
        self._buffer = ""
        if line:
            self.logger.log(self.level, line)


def get_application_log_dir(base_dir: Path | None = None) -> Path:
    return get_logs_dir(base_dir) / "application"


def setup_application_logging(base_dir: Path | None = None) -> tuple[logging.Logger, Path]:
    log_dir = get_application_log_dir(base_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"application_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    console_stream = getattr(sys, "__stdout__", None)
    if console_stream is not None and hasattr(console_stream, "write"):
        console_handler = logging.StreamHandler(console_stream)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(log_file),
        encoding="utf-8",
        mode="a",
        maxBytes=32 * 1024 * 1024,
        backupCount=10,
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    app_logger = logging.getLogger("application")
    app_logger.setLevel(logging.INFO)
    app_logger.info("Application logging initialized. file=%s", str(log_file).replace("\\", "/"))
    return app_logger, log_file


def redirect_std_streams_to_logger(logger: logging.Logger) -> tuple[StreamToLogger, StreamToLogger]:
    stdout_stream = StreamToLogger(logger, logging.INFO)
    stderr_stream = StreamToLogger(logger, logging.ERROR)
    sys.stdout = stdout_stream
    sys.stderr = stderr_stream
    return stdout_stream, stderr_stream
