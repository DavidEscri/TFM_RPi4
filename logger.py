import logging
import os
import time


class Logs:
    def __init__(self):
        self.log_dir = f"logs"
        os.makedirs(self.log_dir, exist_ok=True)

        log_file = os.path.join(self.log_dir, f"logs_tfm_{time.strftime('%Y%m%d')}.log")

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger(__name__)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)

    @classmethod
    def get_logger(cls):
        if not hasattr(cls, "_logger_instance"):
            cls._logger_instance = cls()
        return cls._logger_instance
