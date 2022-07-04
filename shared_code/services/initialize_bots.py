import logging
import os
import random
import json
from typing import Optional, List

from shared_code.models.bot_configuration import BotConfigurationManager, BotConfiguration


class StartService:
	def __init__(self, bot_configuration_manager):
		self.manager: BotConfigurationManager = bot_configuration_manager

	def invoke(self) -> list[str]:
		logging.info(f':: Starting Bot Function Timer')

		configs = list(filter(self.manager.filter_configuration, self.manager.get_configuration()))

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

		return messages
