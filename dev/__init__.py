import json
import logging
import os.path
from typing import Optional

import azure.functions as func

from shared_code.models.bot_configuration import BotConfigurationManager, BotConfiguration


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info(f':: Processing Incoming History For Bot')
    manager = BotConfigurationManager()

    configs = filter(lambda x: x is not None, [filter_configuration(config) for config in get_configuration()])

    for elem in configs:
        logging.info(f":: {elem}")

    return func.HttpResponse("Done", status_code=200)


def filter_configuration(config: BotConfiguration) -> Optional[BotConfiguration]:
    if config.Name is None:
        return None

    if not os.path.exists(config.Model):
        logging.info(f":: {config.Name} does not have a valid model path. Skipping...")
        return None

    if len(config.SubReddits) == 0:
        logging.info(f":: {config.Name} is not configured to run. Skipping...")
        return None

    return config


