import json
import logging
import random

from shared_code.models.bot_configuration import BotConfigurationManager
from shared_code.services.service_container import ServiceContainer


class StartService(ServiceContainer):
	def __init__(self):
		super().__init__()

	def invoke(self) -> list[str]:
		logging.info(f':: Starting Bot Function Timer')

		configs = list(filter(self.bot_configuration_manager.filter_configuration, self.bot_configuration_manager.get_configuration()))

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
