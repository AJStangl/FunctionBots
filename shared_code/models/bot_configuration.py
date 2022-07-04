import json
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class BotConfiguration:
	Name: str
	Model: str
	SubReddits: [str]

	@property
	def __dict__(self):
		"""
		get a python dictionary
		"""
		return asdict(self)

	@property
	def json(self):
		"""
		get the json formated string
		"""
		return json.dumps(self.__dict__)

	@classmethod
	def from_json(cls, json_key, json_string: dict):
		return cls(**json_string[json_key])


class BotConfigurationManager(object):
	def __init__(self):
		self.configurations: [BotConfiguration] = self.get_configuration()

	@staticmethod
	def get_configuration() -> [BotConfiguration]:
		result: [BotConfiguration] = []
		with open("bot_configuration.json") as config:
			for bot_config in json.loads(config.read()):
				deserialized_config = json.dumps(bot_config)
				bot_configuration = json.loads(deserialized_config, object_hook=lambda d: BotConfiguration(**d))
				result.append(bot_configuration)
		return result

	def get_bot_name_list(self) -> [str]:
		configs: [BotConfiguration] = self.get_configuration()
		return [bot.Name for bot in configs]

	@staticmethod
	def match_name(name: str, config: BotConfiguration) -> bool:
		return config.Name.upper() == name.upper()

	def get_configuration_by_name(self, bot_name: str) -> Optional[BotConfiguration]:
		for config in self.configurations:
			if self.match_name(bot_name, config):
				return config
		return None

	@staticmethod
	def filter_configuration(config: BotConfiguration) -> Optional[BotConfiguration]:
		import logging
		import os

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
