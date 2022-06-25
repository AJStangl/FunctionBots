import json
import logging
import os.path
from typing import Optional
import azure.functions as func
import typing
import random

from shared_code.models.bot_configuration import BotConfigurationManager, BotConfiguration

"""
Input: Timer
Output: poll-queue
Queue Message: Bot Configuration 
"""
async def main(initializingTimer: func.TimerRequest, msg: func.Out[typing.List[str]]) -> None:

	logging.info(f':: Starting Bot Function Timer')

	manager = BotConfigurationManager()

	configs = list(filter(filter_configuration, manager.get_configuration()))

	random.shuffle(configs)

	messages = []

	for config in configs:
		message = {
			"Name": config.Name,
			"Model": config.Model,
			"SubReddits": json.dumps(config.SubReddits)
		}

		messages.append(json.dumps(message))

	logging.info(f":: Randomizing the BOIS")
	random.shuffle(messages)

	logging.info(f":: Sending the bois to the front lines!")
	msg.set(messages)

	return None


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