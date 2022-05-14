import os
import logging

from praw import Reddit
from praw.models.reddit.base import RedditBase
from shared_code.models.PrawQueueMessage import PrawQueueMessage


class RedditHelper:
	def __init__(self):
		pass

	@staticmethod
	def get_subs_from_configuration() -> str:
		subs = "+".join(os.environ["SubReddit"].split(","))
		return subs

	@staticmethod
	def get_praw_instance(bot_name: str) -> Reddit:
		logging.info(f":: Initializing Reddit Praw Instance")
		reddit = Reddit(site_name=bot_name)
		return reddit

	@staticmethod
	def get_bot_name() -> str:
		return os.environ["Bot"]

	@staticmethod
	def map_base_to_message(thing: RedditBase, bot_username: str) -> PrawQueueMessage:
		message = PrawQueueMessage(
			source_name=thing.name,
			created_utc=thing.created_utc,
			author=getattr(thing.author, 'name', ''),
			subreddit=thing.subreddit.display_name,
			bot_username=bot_username
		)
		return message
