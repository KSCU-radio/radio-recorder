"""Module for loading configuration from TOML file"""

import re
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import tomli

CONFIG_FILE = "config.toml"


def load_config():
    """Load configuration from TOML file"""
    try:
        if not os.path.exists(CONFIG_FILE):
            raise FileNotFoundError(
                f"Configuration file {CONFIG_FILE} not found. "
                f"Please copy config.toml.example to {CONFIG_FILE} and edit it."
            )

        with open(CONFIG_FILE, "rb") as f:
            return tomli.load(f)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)


# Dictionary mapping string log levels to their actual constants
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def setup_logging(config):
    """Set up logging based on configuration"""
    # Create logger
    root_logger = logging.getLogger()
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set the root logger level
    log_level = config["logging"].get("level", "INFO")
    root_logger.setLevel(LOG_LEVELS.get(log_level, logging.INFO))

    # Set up the rotating file handler
    log_file = config["logging"]["file"]
    max_size = config["logging"]["max_size"]
    backup_count = config["logging"]["backup_count"]
    log_format = config["logging"].get(
        "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_size, backupCount=backup_count, encoding="utf-8"
    )
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)

    # Add a console handler as well
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Configure specific loggers
    if "loggers" in config["logging"]:
        for logger_name, level in config["logging"]["loggers"].items():
            logger = logging.getLogger(logger_name)
            logger.setLevel(LOG_LEVELS.get(level, logging.INFO))

    # Set up a filter for different log categories if filters are configured
    if "filters" in config["logging"]:

        class LogFilter(logging.Filter):
            def __init__(self, config):
                super().__init__()
                self.config = config

            def filter(self, record):
                # Check if the record's category should be filtered
                if "schedule" in record.name.lower() and not self.config.get(
                    "show_schedule", True
                ):
                    return False
                if "api" in record.name.lower() and not self.config.get(
                    "show_api_calls", True
                ):
                    return False
                if "record" in record.name.lower() and not self.config.get(
                    "show_recording", True
                ):
                    return False
                if "email" in record.name.lower() and not self.config.get(
                    "show_email", True
                ):
                    return False
                if "file" in record.name.lower() and not self.config.get(
                    "show_file_ops", True
                ):
                    return False
                return True

        log_filter = LogFilter(config["logging"]["filters"])
        for handler in root_logger.handlers:
            handler.addFilter(log_filter)

    # Reduce verbosity of some third-party libraries
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logging.info("Logging configured successfully")


# Load configuration
config = load_config()

# Access configuration values
EMAIL = config["email"]["address"]
PASSWORD = config["email"]["password"]
API_KEY = config["api"]["spinitron_key"]
STREAM_URL = config["streaming"]["url"]
LOG_FILE = config["logging"]["file"]
MAX_SIZE = config["logging"]["max_size"]
BACKUP_COUNT = config["logging"]["backup_count"]
S3_BUCKET = config["storage"]["s3_bucket"]

# Set up logging
setup_logging(config)

# Create named loggers for different components
logger = logging.getLogger("main")
schedule_logger = logging.getLogger("schedule")
api_logger = logging.getLogger("api")
recording_logger = logging.getLogger("recorder")
email_logger = logging.getLogger("email")
file_logger = logging.getLogger("file_ops")

# Validate EMAIL format
regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
if not re.fullmatch(regex, EMAIL):
    raise ValueError(
        "Invalid sender email address (EMAIL). Please correct it in config.toml."
    )

# Validate PASSWORD format
if not PASSWORD:
    raise ValueError("Password is empty. Please provide a password in config.toml.")

logger.info("Configuration loaded successfully from config.toml")
