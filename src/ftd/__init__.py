"""Root package."""
import logging
import logging.config

__all__ = ["__version__"]
__version__ = "0.1.0"

# logging setup
LOG_FORMAT = "(%(asctime)s) %(levelname)s [%(name)s.%(funcName)s]: %(message)s"
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "defaultFormatter": {"format": LOG_FORMAT, "datefmt": "%H:%M:%S"}
    },
    "handlers": {
        "defaultHandler": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "defaultFormatter",
        }
    },
    "loggers": {
        __name__: {
            "level": "INFO",
            "propagate": False,
            "handlers": ["defaultHandler"],
        },
    },
}
logging.config.dictConfig(LOG_CONFIG)
LOG = logging.getLogger(__name__)
