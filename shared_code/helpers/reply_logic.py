import logging
import os
import random
from datetime import datetime
from typing import Optional

import praw
from praw import Reddit
from praw.models import Message, Redditor, Submission, Comment
from praw.models.reddit.base import RedditBase
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.models.bot_configuration import BotConfigurationManager


class ReplyLogic:
	def __init__(self, instance: Reddit):
		self._own_comment_reply_boost: float = 0.8
		self._interrogative_reply_boost: float = 0.6
		self._new_submission_reply_boost: float = 1.0
		self._human_author_reply_boost: float = 1.0
		self._bot_author_reply_boost: float = 0.5
		self._comment_depth_reply_penalty: float = 0.1
		self._base_reply_probability: float = 0
		self._do_not_reply_bot_usernames = []
		self._message_mention_reply_probability: float = 1.0
		self._praw: Reddit = instance
		self._own_submission_reply_boost: float = 0.8

	def calculate_reply_probability(self, redditBase: RedditBase):
		bot_manager: BotConfigurationManager = BotConfigurationManager()

		bot_names = bot_manager.get_bot_name_list()

		user: Redditor = self._praw.user.me()

		if isinstance(redditBase, Submission):
			return 101

		if isinstance(redditBase, Message):
			return 101

		if isinstance(redditBase, Comment):
			return self.handle_reply_comment_logic(redditBase, bot_names, user)

	def handle_reply_comment_logic(self, comment: Comment, bot_names: [str], user: Redditor) -> float:

		submission: Submission = self._get_submission_from_comment(comment)

		comment_author: Redditor = comment.author

		submission_created_utc = submission.created_utc

		if comment_author.name not in bot_names:
			logging.info(f":: Human Author comment for {comment_author.name}")
			return 101

		if comment_author.name == user.name:
			logging.info(f":: Ignoring Comment Where author and responding bot are the same for {user.name}")
			return 0

		if comment_author.name in self._do_not_reply_bot_usernames:
			logging.info(f":: Ignoring Comment author is in the do not reply list for {user.name}")
			return 0

		text_content = comment.body

		if getattr(comment, 'type', '') == 'username_mention':
			return 101

		if user.name in text_content:
			return self._message_mention_reply_probability * 100

		max_replies = 3
		num_replies = self._get_reply_count(comment)
		if num_replies > max_replies:
			logging.info(f":: Comment has {num_replies} and exceeds {max_replies}")
			return 0

		max_comments: int = 250
		if submission.num_comments > max_comments:
			logging.info(f":: Ignoring Comment to Submission with {max_comments} comments")
			return 0

		time_since_original_post: int = max(0, RedditManager.timestamp_to_hours(submission.created_utc) - 4)

		if time_since_original_post > 12:
			logging.info(f":: Ignoring Comment to Submission with {time_since_original_post} > 12 for {user.name}")
			return 0

		max_depth: int = 12
		comment_depth = self._find_depth_of_comment(comment)

		if comment_depth > max_depth:
			logging.info(f":: Comment depth {comment_depth} exceeds {max_depth} for {user.name}")
			return 0

		base_probability = self._base_reply_probability

		base_probability -= ((comment_depth - 1) * self._comment_depth_reply_penalty)

		if comment.author.name in bot_names:
			base_probability += self._bot_author_reply_boost
		else:
			base_probability += self._human_author_reply_boost

		if self._get_interrogative_reply(text_content):
			base_probability += self._interrogative_reply_boost

		if submission.author == user.name:
			base_probability += self._own_submission_reply_boost

		if comment.parent().author.name == user.name:
			base_probability += self._own_comment_reply_boost

		reply_probability = min(base_probability, 1)

		age_of_submission = (datetime.utcnow() - datetime.utcfromtimestamp(submission_created_utc)).total_seconds() / 3600

		rate_of_decay = max(0, 1 - (age_of_submission / 24))

		return round(reply_probability * rate_of_decay, 2) * 100

	def _get_submission_from_comment(self, comment: Comment) -> Optional[Submission]:
		try:
			sub_id = comment.submission.id
			submission: Submission = self._praw.submission(id=sub_id)
			return submission
		except Exception as e:
			logging.error(e)
			return None

	@staticmethod
	def _find_depth_of_comment(praw_comment) -> int:
		refresh_counter = 0
		# it's a 1-based index so init the counter with 1
		depth_counter = 1
		ancestor = praw_comment
		while not ancestor.is_root:
			depth_counter += 1
			ancestor = ancestor.parent()
			if refresh_counter % 9 == 0:
				try:
					ancestor.refresh()
				except praw.exceptions.ClientException:
					# An error can occur if a message is missing for some reason.
					# To keep the bot alive, return early.
					logging.exception("Exception when counting the comment depth. returning early.")
					return depth_counter

				refresh_counter += 1
		return depth_counter

	@staticmethod
	def _get_reply_count(comment: Comment) -> int:
		comment.reply_sort = "old"
		comment.refresh()
		replies = comment.replies
		num_replies = 0
		for elem in replies:
			if elem is not None:
				num_replies += 1
		return num_replies

	@staticmethod
	def _get_interrogative_reply(text_content) -> bool:
		return any(kw.lower() in text_content.lower() for kw in ['?', ' you', 'what', 'how', 'when', 'why'])
