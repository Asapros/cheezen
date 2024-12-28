from logging import getLogger
from logging.config import dictConfig

import yaml


def setup_logger(config_file):
    with open(config_file, "r") as file:
        config = yaml.safe_load(file)
        dictConfig(config)


logger = getLogger("cheezen")
