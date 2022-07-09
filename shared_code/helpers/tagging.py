import codecs
import logging
import re
from typing import Union

import asyncpraw
import ftfy
from asyncpraw import Reddit
from asyncpraw.models import Submission, Comment, Redditor
from asyncpraw.models.reddit.base import RedditBase


class TaggingMixin:
	"""
	This mixin contains all the logic for tagging comments,
	It is abstracted so that users can update this code on their fork,
	while taking updates on the main classes.
	"""

	_link_submission_start_tag = '<|sols|>'
	_selftext_submission_start_tag = '<|soss|>'

	_title_start_tag = '<|sot|>'
	_selftext_start_tag = '<|sost|>'

	_reply_start_tag = '<|sor|>'
	_reply_end_tag = '<|eor|>'

	_end_tag = '<|'

	def __init__(self, reddit: Reddit):
		self.reddit_instance = reddit

	async def collate_tagged_comment_history(self, loop_thing: RedditBase, to_level=12, use_reply_sense=True) -> str:
		"""
		Loop backwards (upwards in reddit terms) from the praw_thing through the comment up x times,
		tagging the content text in the same way as the training data is
		The resulting string will be passed to the model to generate a reply to
		*This section is customisable for your own bot and how it has been finetuned*
		Each <|tag|> behaves as metadata so the model knows the general writing style of
		titles, replies and so forth.
		"""
		counter = 0
		prefix = ''
		await loop_thing.load()
		while loop_thing and counter < to_level:

			if isinstance(loop_thing, Submission):
				tagged_text = await self.tag_submission(loop_thing, use_reply_sense)
				prefix = tagged_text + prefix

				# can't go any higher than a submission, so break the loop
				break

			elif isinstance(loop_thing, Comment):
				# It's a comment
				tagged_text = await self.tag_comment(loop_thing, use_reply_sense)
				prefix = tagged_text + prefix
				loop_thing = await loop_thing.parent()

			counter += 1

		return prefix

	async def get_reply_tag(self, thing: RedditBase, bot_username, use_reply_sense=True) -> str:
		"""
		Get the reply tag to use.
		The model will generate text after this reply tag.

		*This section is customisable for your own bot and how it has been finetuned*
		"""
		try:
			if isinstance(thing, Comment):
				comment = thing
				await comment.load()
				submission_id = comment.submission.id
				submission = await self.reddit_instance.submission(id=submission_id, fetch=True)

				await submission.load()

				# If the submission is the same as the responding bot use the <|soopr|> tag
				if submission.author == comment.author:
					return '<|soopr|>'

				parent_of_parent = await self.get_parent_of_parent(comment)

				# if the parent's parent was by the author bot, use the own content tag
				if parent_of_parent.author == bot_username:
					return '<|soocr|>'

			if isinstance(thing, Submission):
				return self._reply_start_tag

		except Exception as e:
			logging.info(f":: {e} in get_reply_tag")
			pass

		# It's just a straight reply
		return self._reply_start_tag

	def get_random_new_submission_tag(self, subreddit: str, use_reply_sense=True):
		import random
		# random is already seeded in reddit_io init
		random_value = random.random()

		tag = ''

		if random_value < 0:
			# Make a link (image) post
			tag += '<|sols'
		else:
			# Make a text post
			tag += '<|soss'

		if use_reply_sense:
			tag += f' r/{subreddit}|>'
		else:
			tag += '|>'

		return tag + self._title_start_tag

	async def tag_submission(self, submission: Submission, use_reply_sense=True):
		tagged_text = ""
		await submission.load()

		if submission.is_self:
			tagged_text += "<|soss"
		else:
			tagged_text += "<|sols"

		if use_reply_sense:
			tagged_text += f" r/{submission.subreddit}|>"
		else:
			tagged_text += "|>"

		# prepend the tagged text
		if submission.is_self:

			selftext = submission.selftext

			if hasattr(submission, 'poll_data'):
				for option in submission.poll_data.options:
					selftext += f" - {option.text}"

			# selftext submission
			tagged_text += f"<|sot|>{submission.title}<|eot|><|sost|>{selftext}<|eost|>"

		else:
			# it's a link submission
			tagged_text += f"<|sot|>{submission.title}<|eot|><|sol|><|eol|>"

		return tagged_text

	async def tag_comment(self, comment: Comment, use_reply_sense=True):
		try:
			submission_id = comment.submission.id
			submission: Submission = await self.reddit_instance.submission(id=submission_id)
			await submission.load()
			await comment.load()

			if submission.author.name == comment.author.name:
				return f'<|soopr u/{comment.author}|>{comment.body}<|eoopr|>'

			parent_parent = await self.get_parent_of_parent(comment)

			await parent_parent.load()

			if parent_parent.author.name == comment.author.name:
				return f'<|soocr u/{comment.author}|>{comment.body}<|eoocr|>'
			else:
				return f'<|sor u/{comment.author}|>{comment.body}<|eor|>'

		except Exception as e:
			logging.error(f"{e} in tag_comment")
			return f'<|sor|>{comment.body}<|eor|>'

	def tag_message(self, thing, use_reply_sense=True):

		tagged_text = ""

		if not thing.parent_id:
			# If parent_id property is None then it is the first message of the chain
			tagged_text += f'<|sot>{thing.subject}<|eot|>'

		if use_reply_sense:
			tagged_text += f'<|soocr|>{thing.body}<|eoocr|>'
		else:
			tagged_text += f'<|sor|>{thing.body}<|eor|>'

		return tagged_text

	def extract_reply_from_generated_text(self, prompt: str, generated_text: str) -> dict:

		if prompt is None or generated_text is None:
			return {}

		# remove any cruft
		generated_text = generated_text.replace('&amp;#x200B;\n', '')

		# find the first instance of the end-of-comment tag, starting from the end of the prompt
		index_of_truncate = generated_text.find(self._end_tag, len(prompt))

		if index_of_truncate == -1:
			# the original truncate tag couldn't be found,
			# but we'll still try and truncate the string at the last line break (end of paragraph)
			# so that the text still looks clean.
			index_of_truncate = generated_text.rfind("\\n")

		if index_of_truncate == -1:
			# in case trained model do not output tags and put lot !!!!! at the end,
			# This change allows this messages without need of end tags
			index_of_truncate = generated_text.find("!!!!")

		if index_of_truncate == -1:
			# still nothing could be found so just skip this one
			# if this is hit often, increase the length of the generated text
			return {}

		# extract the text from between the prompt and the truncate point
		reply_body = generated_text[len(prompt):index_of_truncate]
		if reply_body:
			return {'body': self._decode_generated_text(reply_body)}

		# Return nothing
		return {}

	def extract_title_from_generated_text(self, generated_text):

		idx_title_start = generated_text.find(self._title_start_tag)

		idx_title_end = generated_text.find(self._end_tag, (idx_title_start + len(self._title_start_tag)))

		if idx_title_start == -1 or idx_title_end == -1:
			# There must be at least a complete title to make a submission
			return None

		title_text = generated_text[idx_title_start + len(self._title_start_tag):idx_title_end]

		if 0 < len(title_text) < 300:
			# Validate the title length is within reddit's range
			return self._decode_generated_text(title_text)

	def extract_selftext_from_generated_text(self, generated_text):

		idx_st_start = generated_text.find(self._selftext_start_tag)

		idx_st_end = generated_text.find(self._end_tag, (idx_st_start + len(self._selftext_start_tag)))

		if idx_st_start == -1 or idx_st_end == -1:
			return None

		selftext_text = generated_text[idx_st_start + len(self._selftext_start_tag):idx_st_end]

		return self._decode_generated_text(selftext_text)

	def extract_submission_from_generated_text(self, generated_text):

		return_dict = {}

		if generated_text is None:
			return {}

		# remove any cruft
		generated_text = generated_text.replace('&amp;#x200B;\n', '')

		title = self.extract_title_from_generated_text(generated_text)

		if not title:
			return {}
		else:
			# The title is ok, add it to the dict to return
			return_dict['title'] = title

		selftext = self.extract_selftext_from_generated_text(generated_text)

		if selftext:
			return_dict['selftext'] = selftext

		return return_dict

	def remove_tags_from_string(self, input_string):
		# Removes any <|sor u/user|>, <|sost|> etc from a string
		return re.sub(r'(\<\|[\w\/ ]*\|\>)', ' ', input_string).strip()

	def _decode_generated_text(self, text):
		return ftfy.fix_text(codecs.decode(text, "unicode_escape"))

	def remove_username_mentions_from_string(self, string: str, username: str) -> str:
		regex = re.compile(fr"u\/{username}(?!\|\>)", re.IGNORECASE)
		return regex.sub('', string)

	async def get_parent_of_parent(self, comment: RedditBase) -> RedditBase:
		# Don't get the parent of a submission
		if isinstance(comment, Submission):
			await comment.load()
			return comment

		# First get the parent.
		parent = await comment.parent()

		# If it's a submission then return the parent
		if isinstance(parent, Submission):
			return parent

		# Force re-fresh to load parent
		await parent.refresh()
		if parent:
			try:
				parent_parent = await parent.parent()
				# Check if parent is not a submission and refresh it.
				if parent_parent and not isinstance(parent_parent, Submission):
					await parent_parent.refresh()
					return parent_parent
				else:
					# Otherwise return the submission
					return parent_parent
			except Exception as e:
				logging.info(f":: Error getting parent of parent {e}")

