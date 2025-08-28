import os
import logging
from datetime import datetime

class Logger:
    SUCCESS_LEVEL = 25
    SKIPPED_LEVEL = 35

    def __init__(self, filename, log_dir="logs"):
        self.filename = filename
        self.log_dir = log_dir

        # Create logs directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)

        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = os.path.join(self.log_dir, f"{self.filename}_{timestamp}.log")

        # Set up the logger
        self.logger = logging.getLogger(self.filename)
        self.logger.setLevel(logging.DEBUG)

        # Register custom log levels
        logging.addLevelName(self.SUCCESS_LEVEL, "SUCCESS")
        logging.addLevelName(self.SKIPPED_LEVEL, "SKIPPED")

        # Avoid adding multiple handlers if logger already exists
        if not self.logger.handlers:
            formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', 
                                        datefmt='%Y-%m-%d %H:%M:%S')

            # File handler
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)


    def info(self, message):
        self.logger.info(message)

    def error(self, message):
        self.logger.error(message)

    def warning(self, message):
        self.logger.warning(message)

    def debug(self, message):
        self.logger.debug(message)

    def success(self, message):
        self.logger.log(self.SUCCESS_LEVEL, message)

    def skipped(self, message):
        self.logger.log(self.SKIPPED_LEVEL, message)

    def get_log_file_path(self):
        """Return the full path of the generated log file."""
        return self.log_file
