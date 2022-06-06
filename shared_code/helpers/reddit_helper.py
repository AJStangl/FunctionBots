import os
import logging
from datetime import datetime

from asyncpraw import Reddit
from asyncpraw.models.reddit.base import RedditBase

from shared_code.models.bot_configuration import BotConfigurationManager
from shared_code.models.table_data import TableRecord, Status


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
	def map_base_to_message(thing: RedditBase, bot_username: str, input_type: str) -> TableRecord:
		message = TableRecord(
			PartitionKey=bot_username,
			RowKey=f"{bot_username}|{input_type}|{thing.id}",
			id=thing.id,
			name_id=thing.id,
			subreddit=thing.subreddit.display_name,
			input_type=input_type,
			content_date_submitted_utc=thing.created,
			author=getattr(thing.author, 'name', ''),
			responding_bot=bot_username,
			text_generation_prompt="",
			text_generation_response="",
			has_responded=False,
			status=0,
			time_in_hours=(datetime.utcnow() - datetime.fromtimestamp(thing.created)).total_seconds() / 3600
		)
		return message
