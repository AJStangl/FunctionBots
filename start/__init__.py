import json
import logging
import os.path
from typing import Optional
import azure.functions as func
import typing

from shared_code.models.bot_configuration import BotConfigurationManager, BotConfiguration


def main(initializingTimer: func.TimerRequest, msg: func.Out[typing.List[str]]) -> None:
	logging.info(f':: Starting Process')
	manager = BotConfigurationManager()

	configs = list(filter(filter_configuration, manager.get_configuration()))

	messages = []

	for item in configs:
		foo = {
			"Name": item.Name,
			"Model": item.Model,
			"SubReddits": json.dumps(item.SubReddits)
		}

		messages.append(json.dumps(foo))

	msg.set(messages)


def filter_configuration(config: BotConfiguration) -> Optional[BotConfiguration]:

	if config.Name is None:
		return None

	if not os.path.exists(config.Model):
		logging.info(f":: {config.Name} does not have a valid model path. Skipping...")
		return None

	if len(config.SubReddits) == 0:
		logging.info(f":: {config.Name} is not configured to run. Skipping...")
		return None

	logging.info(f":: {config.Name} sent for processing")

	return config