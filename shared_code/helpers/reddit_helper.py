import logging
import datetime

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

	@staticmethod
	def timestamp_to_hours(utc_timestamp: int, adjustment_for_timezone=4):
		return int((datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(
			utc_timestamp)).total_seconds() / 3600) - adjustment_for_timezone

	@staticmethod
	def chain_listing_generators(*iterables):
		# Special tool for chaining PRAW's listing generators
		# It joins the three iterables together so that we can DRY
		for it in iterables:
			for element in it:
				if element is None:
					break
				else:
					yield element
