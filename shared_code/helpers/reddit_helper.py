import os
import logging
from typing import Optional

from praw import Reddit
from praw.models.reddit.base import RedditBase
from shared_code.models.praw_content_message import PrawQueueMessage


class RedditHelper:
	def __init__(self):
		self.instance: dict[str, Reddit] = dict()

	@staticmethod
	def get_subs_from_configuration() -> str:
		subs = "+".join(os.environ["SubReddit"].split(","))
		return subs

	def get_praw_instance(self, bot_name: str) -> Reddit:

		cached_instance = self.instance.get(bot_name)

		if cached_instance:
			logging.info(f":: Using Cached PRAW Instance for {bot_name}")
			return cached_instance

		logging.info(f":: Initializing Reddit Praw Instance for {bot_name}")
		reddit = Reddit(site_name=bot_name)
		self.instance[bot_name] = reddit

		return reddit

	@staticmethod
	def get_bot_name() -> str:
		return os.environ["Bot"]

	@staticmethod
	def map_base_to_message(thing: RedditBase, bot_username: str, input_type: str) -> PrawQueueMessage:
		message = PrawQueueMessage(
			input_type=input_type,
			source_name=thing.name,
			created_utc=thing.created_utc,
			author=getattr(thing.author, 'name', ''),
			subreddit=thing.subreddit.display_name,
			bot_username=bot_username
		)
		return message
