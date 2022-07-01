import logging
import os
from datetime import datetime

import praw
from praw import Reddit
from praw.models import Message
from praw.models.reddit.base import RedditBase
from praw.reddit import Submission, Comment
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

	def calculate_reply_probability(self, praw_thing: RedditBase):

		if not praw_thing.author:
			return 0
		elif praw_thing.author.name.lower() == self._praw.user.me().name.lower():
			return 0
		elif praw_thing.author.name.lower() in self._do_not_reply_bot_usernames:
			return 0

		thing_text_content = ''
		submission_link_flair_text = ''
		submission_created_utc = None
		is_own_comment_reply = False

		if isinstance(praw_thing, Submission):
			return 101
			# object is a submission that has title and selftext
			thing_text_content = f'{praw_thing.title} {praw_thing.selftext}'
			submission_link_flair_text = praw_thing.link_flair_text or ''
			submission_created_utc = datetime.utcfromtimestamp(praw_thing.created_utc)

		elif isinstance(praw_thing, Comment):
			thing_text_content = praw_thing.body
			submission_link_flair_text = praw_thing.submission.link_flair_text or ''
			submission_created_utc = datetime.utcfromtimestamp(praw_thing.submission.created_utc)
			is_own_comment_reply = praw_thing.parent().author == self._praw.user.me().name

		elif isinstance(praw_thing, Message):
			thing_text_content = praw_thing.body
			submission_created_utc = datetime.utcfromtimestamp(praw_thing.created_utc)

		if getattr(praw_thing, 'type', '') == 'username_mention' or self._praw.user.me().name.lower() in thing_text_content.lower() or isinstance(praw_thing, Message):
			return self._message_mention_reply_probability * 100

		base_probability = self._base_reply_probability

		# Global comment handling
		if isinstance(praw_thing, Comment):
			num_comments_for_submission = self._get_comments_per_submission(praw_thing)
			if num_comments_for_submission > 250:
				return 0

			time_of_submission_in_hours = self._get_time_from_sub_to_reply(praw_thing)
			if time_of_submission_in_hours > 12:
				return 0

			comment_depth = self._find_depth_of_comment(praw_thing)
			if comment_depth > 12:
				return 0
			else:
				base_probability -= ((comment_depth - 1) * self._comment_depth_reply_penalty)

		if 'verified gpt-2' in (getattr(praw_thing, 'author_flair_text', '') or '').lower() or any(praw_thing.author.name.lower().endswith(i) for i in ['ssi', 'bot', 'gpt2']):
			base_probability += self._bot_author_reply_boost
		else:
			base_probability += self._human_author_reply_boost

		if isinstance(praw_thing, Submission):
			base_probability += self._new_submission_reply_boost

		if isinstance(praw_thing, Submission) or is_own_comment_reply:
			if any(kw.lower() in thing_text_content.lower() for kw in ['?', ' you', 'what', 'how', 'when', 'why']):
				base_probability += self._interrogative_reply_boost

		if isinstance(praw_thing, Comment):
			try:
				if praw_thing.parent().author == self._praw.user.me().name:
					base_probability += self._own_comment_reply_boost
			except Exception as e:
				logging.error(f":: Problem obtaining parent().author", e)
				pass

			if praw_thing.submission.author == self._praw.user.me().name:
				base_probability += self._own_submission_reply_boost

		reply_probability = min(base_probability, 1)

		age_of_submission = (datetime.utcnow() - submission_created_utc).total_seconds() / 3600

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

	def _get_comments_per_submission(self, comment: Comment) -> int:
		sub_id = comment.submission.id
		submission: Submission = self._praw.submission(id=sub_id)
		return submission.num_comments

	def _get_time_from_sub_to_reply(self, comment: Comment):
		sub_id = comment.submission.id
		submission: Submission = self._praw.submission(id=sub_id)
		time_since_original_post: int = max(0, RedditManager.timestamp_to_hours(submission.created_utc) - 4)
		return time_since_original_post
