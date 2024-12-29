import os
from logging import getLogger
from logging.config import dictConfig

import yaml

DEFAULT_LOG_LEVEL = "INFO"


def setup_logger(config_file, log_level):
    with open(config_file, "r") as file:
        config = yaml.safe_load(file.read().replace("${LOGLEVEL}", (log_level or DEFAULT_LOG_LEVEL).upper()))
        dictConfig(config)
    if log_level is None:
        logger.warning("LOGLEVEL not configured. Defaulting to {}".format(DEFAULT_LOG_LEVEL))


logger = getLogger("cheezen")
