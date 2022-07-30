import json
import logging
import typing

import azure.functions as func
import random

from shared_code.models.bot_configuration import BotConfigurationManager, BotConfiguration


async def main(submissionTimer: func.TimerRequest, responseMessage: func.Out[typing.List[str]]) -> None:
	logging.info(f":: Submission Creation Trigger Called")
	manager: BotConfigurationManager = BotConfigurationManager()
	configs: [BotConfiguration] = list(filter(manager.filter_configuration, manager.get_configuration()))
	messages: [str] = []
	for bot_config in configs:
		for sub in bot_config.SubReddits:
			message = {
				"Name": bot_config.Name,
				"Model": bot_config.Model,
				"SubReddit": sub
			}
			messages.append(json.dumps(message))

	final_message = random.choice(messages)
	responseMessage.set([final_message])
	return None
