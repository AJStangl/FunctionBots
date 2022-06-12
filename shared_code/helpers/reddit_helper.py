import logging

from praw import Reddit

from shared_code.models.bot_configuration import BotConfigurationManager


class RedditManager:
	def __init__(self):
		self.bot_config_manager: BotConfigurationManager = BotConfigurationManager()

	def get_subs_from_configuration(self, bot_name: str) -> str:
		subs = "+".join(self.bot_config_manager.get_configuration_by_name(bot_name).SubReddits)
		return subs

	@staticmethod
	def get_praw_instance_for_bot(bot_name: str) -> Reddit:
		logging.debug(f":: Initializing Reddit Praw Instance for {bot_name}")
		reddit = Reddit(site_name=bot_name)
		return reddit