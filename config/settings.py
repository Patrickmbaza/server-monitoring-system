import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Monitoring Settings
CHECK_INTERVAL = 60  # seconds
TIMEOUT = 10  # seconds for connection timeout
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


# WhatsApp Configuration (using Twilio API)
def _clean_phone_numbers(numbers_str: str) -> list:
    """Clean and validate phone numbers from environment variable"""
    if not numbers_str:
        return []

    numbers = []
    for num in numbers_str.split(","):
        num = num.strip()
        if num:  # Only add non-empty strings
            numbers.append(num)
    return numbers


WHATSAPP_CONFIG = {
    "account_sid": os.getenv("TWILIO_ACCOUNT_SID", ""),
    "auth_token": os.getenv("TWILIO_AUTH_TOKEN", ""),
    "from_number": os.getenv("TWILIO_WHATSAPP_NUMBER", ""),
    "admin_numbers": _clean_phone_numbers(os.getenv("ADMIN_WHATSAPP_NUMBERS", "")),
    "user_numbers": _clean_phone_numbers(os.getenv("USER_WHATSAPP_NUMBERS", "")),
    "critical_numbers": _clean_phone_numbers(
        os.getenv("CRITICAL_WHATSAPP_NUMBERS", "")
    ),
}

# Microsoft Teams Configuration
TEAMS_CONFIG = {
    "admin_webhook": os.getenv("TEAMS_ADMIN_WEBHOOK", ""),
    "user_webhook": os.getenv("TEAMS_USER_WEBHOOK", ""),
}

# Create logs directory if it doesn't exist
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Logging Configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "monitoring.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "standard",
        },
        "error_file": {
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "monitoring_error.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "detailed",
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "monitoring": {
            "handlers": ["file", "error_file", "console"],
            "level": "INFO",
            "propagate": True,
        },
        "twilio": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "urllib3": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
