import codecs
import re

import ftfy
from praw.models import Submission, Comment
from praw.models.reddit.base import RedditBase


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

	def collate_tagged_comment_history(self, loop_thing: RedditBase, to_level=12, use_reply_sense=True):
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

		while loop_thing and counter < to_level:

			if isinstance(loop_thing, Submission):
				tagged_text = self.tag_submission(loop_thing, use_reply_sense)
				prefix = tagged_text + prefix

				# can't go any higher than a submission, so break the loop
				break

			elif isinstance(loop_thing, Comment):
				# It's a comment
				tagged_text = self.tag_comment(loop_thing, use_reply_sense)
				prefix = tagged_text + prefix

				loop_thing = loop_thing.parent()

			counter += 1

		return prefix

	def get_reply_tag(self, thing: RedditBase, bot_username, use_reply_sense=True):
		"""
		Get the reply tag to use.
		The model will generate text after this reply tag.

		*This section is customisable for your own bot and how it has been finetuned*
		"""
		if use_reply_sense:
			if isinstance(thing, Comment):
				# Need this praw_Comment check for message replies
				if thing.submission:
					# The submission was by the bot so use special tag
					if thing.submission.author.name.lower() == bot_username.lower():
						return '<|soopr|>'
				if thing.parent():
					# if the parent's parent was by the author bot, use the own content tag
					if thing.parent().author.name.lower() == bot_username.lower():
						return '<|soocr|>'

		# It's just a straight reply
		return self._reply_start_tag

	def get_random_new_submission_tag(self, subreddit, use_reply_sense=True):
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

	def tag_submission(self, thing: Submission, use_reply_sense=True):
		tagged_text = ""

		if thing.is_self:
			tagged_text += "<|soss"
		else:
			tagged_text += "<|sols"

		if use_reply_sense:
			tagged_text += f" r/{thing.subreddit}|>"
		else:
			tagged_text += "|>"

		# prepend the tagged text
		if thing.is_self:

			selftext = thing.selftext

			if hasattr(thing, 'poll_data'):
				# The submission has a poll - extract that data
				for option in thing.poll_data.options:
					# Replicate unordered list markdown,
					# appeding it to the end of the selftext
					selftext += f" - {option.text}"

			# selftext submission
			tagged_text += f"<|sot|>{thing.title}<|eot|><|sost|>{selftext}<|eost|>"

		else:
			# it's a link submission
			tagged_text += f"<|sot|>{thing.title}<|eot|><|sol|><|eol|>"

		return tagged_text

	def tag_comment(self, thing, use_reply_sense=True):
		if use_reply_sense:

			if thing.submission.author.name == thing.author:
				return f'<|soopr u/{thing.author}|>{thing.body}<|eoopr|>'

			parent_parent = None
			try:
				parent_parent = thing.parent().parent()
				if parent_parent.author.name == thing.author:
					return f'<|soocr u/{thing.author}|>{thing.body}<|eoocr|>'
			except:
				# Exception will be raised if there are not two parents
				pass

			return f'<|sor u/{thing.author}|>{thing.body}<|eor|>'

		else:
			return f'<|sor|>{thing.body}<|eor|>'

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
