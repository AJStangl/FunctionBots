import logging
import os
from datetime import datetime
from typing import Optional

from asyncpraw import Reddit
from asyncpraw.models import Message, Redditor, Submission, Comment
from asyncpraw.models.reddit.base import RedditBase

from shared_code.helpers.reddit_helper import RedditManager
from shared_code.models.bot_configuration import BotConfigurationManager


class ReplyLogic:
	def __init__(self, instance: Reddit):
		self._reddit_instance: Reddit = instance
		self._base_reply_probability: float = 0.0
		self._own_comment_reply_boost: float = 0.20
		self._interrogative_reply_boost: float = 0.20
		self._human_author_reply_boost: float = 0.20
		self._bot_author_reply_boost: float = 0.20
		self._own_submission_reply_boost: float = 0.20
		self._do_not_reply_bot_usernames = []
		self._comment_depth_reply_penalty: float = 0.1
		self.max_time_since_submission: int = int(os.environ["MaxTimeSinceSubmission"])
		self.max_comments: int = int(os.environ["MaxComments"])
		self._known_bot_names: [str] = os.environ["KnownBots"].split(",")

	async def calculate_reply_probability(self, redditBase: RedditBase):

		bot_manager: BotConfigurationManager = BotConfigurationManager()

		bot_names = bot_manager.get_bot_name_list()

		user: Redditor = await self._reddit_instance.user.me()

		if isinstance(redditBase, Submission):
			return await self._handle_submission_logic(redditBase, user)

		if isinstance(redditBase, Message):
			return 101

		if isinstance(redditBase, Comment):
			return await self._handle_reply_comment_logic(redditBase, bot_names, user)

	async def _handle_submission_logic(self, submission: Submission, reddit_user: Redditor) -> float:
		# Ignore when submission is the same for the submitter and responder
		await reddit_user.load()
		await submission.load()
		if reddit_user.name == getattr(submission.author, 'name', ''):
			return 0.0

		max_time_since_submission: int = self.max_time_since_submission
		time_since_original_post: int = max(0, RedditManager.timestamp_to_hours(submission.created_utc))
		if time_since_original_post > max_time_since_submission:
			logging.debug(f":: Ignoring Submission with time_since_original_post: {time_since_original_post} > max_time_since_submission: {max_time_since_submission} for {reddit_user.name}")
			return 0.0

		else:
			return 101.0

	async def _handle_reply_comment_logic(self, comment: Comment, bot_names: [str], user: Redditor) -> float:

		submission: Submission = await self._get_submission_from_comment(comment)

		comment_author: Redditor = comment.author

		submission_created_utc = submission.created_utc

		################################################################################################################
		# Logic for Always replying
		# Account for:
		# - Username mentions
		# - Replying to a bot not part of the bot configuration
		# - Username in text of comment
		################################################################################################################

		# Always reply to a username mention
		if getattr(comment, 'type', '') == 'username_mention':
			logging.info(f":: User name mention detected for {user.name}")
			return 101.0

		# Always reply if the author is not in the configuration
		if comment_author.name not in bot_names + self._known_bot_names:
			logging.info(f":: Human Author comment for {comment_author.name}")
			return 101

		# Always respond if the name of the bot is in the text of the comment
		text_content = comment.body
		if user.name in text_content:
			return 101.0

		################################################################################################################
		# Logic for Always Ignoring
		# Account for:
		# - Comment Author is the name as the responder
		# - In a do not reply list
		# - Max reply for a comment reply exceeded
		# - Max comments for a submission exceeded
		# - Max time for a submission exceeded
		# - Max depth for comment in submission exceeded
		################################################################################################################

		# Ensure responding bot is not the same as the comments author
		if user.name == getattr(comment.author, 'name', '') or comment_author.name == user.name:
			logging.debug(f":: Comment Author {comment_author} is the name as {user.name}")
			return 0.0

		# Ensure that the bot does not respond to something in the do-not-reply list
		if comment_author.name in self._do_not_reply_bot_usernames:
			logging.debug(f":: Ignoring Comment author is in the do not reply list for {user.name}")
			return 0.0

		# Try to prevent all bots replying to a comment.
		# max_replies = 3
		# num_replies = await self._get_reply_count(comment)
		# if num_replies > max_replies:
		# 	logging.info(f":: Comment has {num_replies} and exceeds {max_replies}")
		# 	return 0

		# Try to prevent exceeding 250 comments for a submission
		if submission.num_comments > self.max_comments:
			logging.debug(f":: Ignoring Comment to Submission with {self.max_comments} comments")
			return 0

		# Try to ensure the max skew time from the submission is in range to reply
		time_since_original_post: int = max(0, RedditManager.timestamp_to_hours(submission.created_utc))
		if time_since_original_post > self.max_time_since_submission:
			logging.debug(f":: Ignoring Comment to Submission with time since post: {time_since_original_post} > {self.max_time_since_submission} for {user.name}")
			return 0

		# Try to prevent going to deep into the comment forest
		max_depth: int = 6
		comment_depth = await self._find_depth_of_comment(comment)
		if comment_depth > max_depth:
			logging.debug(f":: Comment depth {comment_depth} exceeds {max_depth} for {user.name}")
			return 0.0

		################################################################################################################
		# Logic for reply-probability
		# Account for:
		# - Reduce probability with comment depth
		# - Comment author is known
		# - Comment author is not a bot known in configuration
		# - Interrogative Text
		# - Replying to own submission
		# - Replying to comment to a comment
		# - Apply decay rate to probability
		################################################################################################################
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

		comment_parent = await comment.parent()

		await comment_parent.load()

		try:
			if comment_parent.author.name == user.name:
				base_probability += self._own_comment_reply_boost
		except Exception as e:
			logging.error(e)
			pass

		reply_probability = min(base_probability, 1)

		age_of_submission = (datetime.utcnow() - datetime.utcfromtimestamp(submission_created_utc)).total_seconds() / 3600

		hour_per_day: float = age_of_submission / 24.0
		factor: float = 1.0 - hour_per_day
		factored_decay_probability = reply_probability * factor * 100
		max_probability = max(0.0, factored_decay_probability)
		return max_probability

	async def _get_submission_from_comment(self, comment: Comment) -> Optional[Submission]:
		try:
			sub_id = comment.submission.id
			submission: Submission = await self._reddit_instance.submission(id=sub_id, fetch=True)
			return submission
		except Exception as e:
			logging.error(f":: An exception has occurred at '_get_submission_from_comment' with message: {e}")
			return None

	@staticmethod
	async def _find_depth_of_comment(comment: Comment) -> int:
		refresh_counter = 0
		# it's a 1-based index so init the counter with 1
		depth_counter = 1
		ancestor: Comment = comment
		while not ancestor.is_root:
			depth_counter += 1
			ancestor = await ancestor.parent()
			if refresh_counter % 9 == 0:
				try:
					await ancestor.refresh()
				except Exception as e:
					logging.exception(f":: Exception when counting the comment depth. returning early. {e}")
					return depth_counter
				refresh_counter += 1
		return depth_counter

	@staticmethod
	def _get_interrogative_reply(text_content: str) -> bool:
		return any(kw.lower() in text_content.lower() for kw in ['?', ' you', 'what', 'how', 'when', 'why'])
