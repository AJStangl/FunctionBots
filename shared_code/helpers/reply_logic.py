import logging
from datetime import datetime

import praw
from praw import Reddit
from praw.models import Message
from praw.reddit import Submission, Comment


class ReplyLogic:
	def __init__(self, instance: Reddit):
		self._own_comment_reply_boost = .5
		self._interrogative_reply_boost = .5
		self._new_submission_reply_boost = 1
		self._human_author_reply_boost = 1
		self._bot_author_reply_boost = .8
		self._comment_depth_reply_penalty = 0.05
		self._base_reply_probability = 0
		self._do_not_reply_bot_usernames = None
		self._message_mention_reply_probability = 1
		self._praw: Reddit = instance
		self._own_submission_reply_boost = .8

	def calculate_reply_probability(self, praw_thing):
		# Ths function contains all of the logic used for deciding whether to reply

		if not praw_thing.author:
			# If the praw_thing has been deleted the author will be None,
			# don't proceed to attempt a reply. Usually we will have downloaded
			# the praw_thing before it is deleted so this won't get hit often.
			return 0
		elif praw_thing.author.name.lower() == self._praw.user.me().name.lower():
			# The incoming praw object's author is the bot, so we won't reply
			return 0
		elif praw_thing.author.name.lower() in self._do_not_reply_bot_usernames:
			# Ignore comments/messages from Admins
			return 0

		# merge the text content into a single variable so it's easier to work with
		thing_text_content = ''
		submission_link_flair_text = ''
		submission_created_utc = None
		is_own_comment_reply = False

		if isinstance(praw_thing, Submission):
			# object is a submission that has title and selftext
			thing_text_content = f'{praw_thing.title} {praw_thing.selftext}'
			submission_link_flair_text = praw_thing.link_flair_text or ''
			submission_created_utc = datetime.utcfromtimestamp(praw_thing.created_utc)

		elif isinstance(praw_thing, Comment):
			# otherwise it's a comment
			thing_text_content = praw_thing.body
			# navigate to the parent submission to get the link_flair_text
			submission_link_flair_text = praw_thing.submission.link_flair_text or ''
			submission_created_utc = datetime.utcfromtimestamp(praw_thing.submission.created_utc)
			is_own_comment_reply = praw_thing.parent().author == self._praw.user.me().name

		elif isinstance(praw_thing, Message):
			thing_text_content = praw_thing.body
			submission_created_utc = datetime.utcfromtimestamp(praw_thing.created_utc)

		# if the bot is mentioned, or its username is in the thing_text_content, reply 100%
		if getattr(praw_thing, 'type', '') == 'username_mention' or\
			self._praw.user.me().name.lower() in thing_text_content.lower() or\
			isinstance(praw_thing, Message):
			return self._message_mention_reply_probability

		# From here we will start to calculate the probability cumulatively
		# Adjusting the weights here will change how frequently the bot will post
		# Try not to spam the sub too much and let other bots and humans have space to post
		base_probability = self._base_reply_probability

		if isinstance(praw_thing, Comment):
			# Find the depth of the comment
			comment_depth = self._find_depth_of_comment(praw_thing)
			if comment_depth > 12:
				# don't reply to deep comments, to prevent bots replying in a loop
				return 0
			else:
				# Reduce the reply probability x% for each level of comment depth
				# to keep the replies higher up
				base_probability -= ((comment_depth - 1) * self._comment_depth_reply_penalty)

		# Check the flair and username to see if the author might be a bot
		# 'Verified GPT-2 Bot' is only valid on r/subsimgpt2interactive
		# Sometimes author_flair_text will be present but None
		if 'verified gpt-2' in (getattr(praw_thing, 'author_flair_text', '') or '').lower()\
			or any(praw_thing.author.name.lower().endswith(i) for i in ['ssi', 'bot', 'gpt2']):
			# Adjust for when the author is a bot
			base_probability += self._bot_author_reply_boost
		else:
			# assume humanoid if author metadata doesn't meet the criteria for a bot
			base_probability += self._human_author_reply_boost

		if isinstance(praw_thing, Submission):
			# it's a brand new submission.
			# This is mostly obsoleted by the depth penalty
			base_probability += self._new_submission_reply_boost

		if isinstance(praw_thing, Submission) or is_own_comment_reply:
			if any(kw.lower() in thing_text_content.lower() for kw in ['?', ' you', 'what', 'how', 'when', 'why']):
				# any interrogative terms in the submission or comment text;
				# results in an increased reply probability
				base_probability += self._interrogative_reply_boost

		if isinstance(praw_thing, Comment):
			if praw_thing.parent().author == self._praw.user.me().name:
				# the post prior to this is by the bot
				base_probability += self._own_comment_reply_boost

			if praw_thing.submission.author == self._praw.user.me().name:
				# the submission is by the bot, and favor that with a boost
				base_probability += self._own_submission_reply_boost

		reply_probability = min(base_probability, 1)
		#
		# work out the age of submission in hours
		age_of_submission = (datetime.utcnow() - submission_created_utc).total_seconds() / 3600
		# calculate rate of decay over x hours
		rate_of_decay = max(0, 1 - (age_of_submission / 24))
		# multiply the rate of decay by the reply probability
		return round(reply_probability * rate_of_decay, 2)

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