import logging
import os
from datetime import datetime
from typing import Optional

import praw
from praw import Reddit
from praw.models import Message, Redditor, Submission, Comment
from praw.models.reddit.base import RedditBase
from shared_code.helpers.reddit_helper import RedditManager


class ReplyLogic:
	def __init__(self, instance: Reddit):
		self._own_comment_reply_boost: float = 0.8
		self._interrogative_reply_boost: float = 0.6
		self._new_submission_reply_boost: float = 1.0
		self._human_author_reply_boost: float = 0.5
		self._bot_author_reply_boost: float = 0.5
		self._comment_depth_reply_penalty: float = 0.1
		self._base_reply_probability: float = 0
		self._do_not_reply_bot_usernames = []
		self._message_mention_reply_probability: float = 1.0
		self._praw: Reddit = instance
		self._own_submission_reply_boost: float = 0.8

	def calculate_reply_probability(self, redditBase: RedditBase):

		user: Redditor = self._praw.user.me()
		# Always respond to a submission
		if isinstance(redditBase, Submission):
			submission: Submission = redditBase
			submission_created_utc = datetime.utcfromtimestamp(submission.created_utc)
			return 101

		if isinstance(redditBase, Message):
			return 101

		if isinstance(redditBase, Comment):
			comment: Comment = redditBase
			submission: Submission = self._get_submission_from_comment(comment)
			comment_author: Redditor = comment.author
			submission_created_utc = submission.created_utc

			if comment_author.name == user.name:
				logging.info(f":: Ignoring Comment Where author and responding bot are the same for {user.name}")
				return 0

			if comment_author.name in self._do_not_reply_bot_usernames:
				logging.info(f":: Ignoring Comment author is in the do not reply list for {user.name}")
				return 0

			text_content = comment.body

			if getattr(comment, 'type', '') == 'username_mention':
				return self._message_mention_reply_probability * 100

			if user.name in text_content:
				return self._message_mention_reply_probability * 100

			max_comments: int = 250
			if submission.num_comments > max_comments:
				logging.info(f":: Ignoring Comment to Submission with {max_comments} comments")
				return 0

			time_since_original_post: int = max(0, RedditManager.timestamp_to_hours(submission.created_utc) - 4)

			if time_since_original_post > 12:
				return 0

			max_depth: int = 12
			comment_depth = self._find_depth_of_comment(comment)
			if comment_depth > max_depth:
				logging.info(f":: Comment depth {comment_depth} exceeds {max_depth}")
				return 0

			base_probability = self._base_reply_probability
			base_probability -= ((comment_depth - 1) * self._comment_depth_reply_penalty)

			if any(comment.author.name.lower().endswith(i) for i in ['ssi', 'bot', 'gpt2']):
				base_probability += self._bot_author_reply_boost

			else:
				base_probability += self._human_author_reply_boost

			if any(kw.lower() in text_content.lower() for kw in ['?', ' you', 'what', 'how', 'when', 'why']):
				base_probability += self._interrogative_reply_boost

			if submission.author == user.name:
				base_probability += self._own_submission_reply_boost

			if comment.parent().author.name == user.name:
				base_probability += self._own_comment_reply_boost

			reply_probability = min(base_probability, 1)

			age_of_submission = (datetime.utcnow() - datetime.utcfromtimestamp(submission_created_utc)).total_seconds() / 3600

			rate_of_decay = max(0, 1 - (age_of_submission / 24))

			return round(reply_probability * rate_of_decay, 2) * 100


	def _find_depth_of_comment(self, praw_comment) -> int:
		"""
		Adapted from:
		https://praw.readthedocs.io/en/latest/code_overview/models/comment.html#praw.models.Comment.parent
		Loop back up the tree until reaching the root ancestor
		Returns integer representing the depth
		"""

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


	def _get_submission_from_comment(self, comment: Comment) -> Optional[Submission]:
		try:
			sub_id = comment.submission.id
			submission: Submission = self._praw.submission(id=sub_id)
			return submission
		except Exception as e:
			logging.error(e)
			return None


