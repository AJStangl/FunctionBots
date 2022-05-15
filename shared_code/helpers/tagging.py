from praw.models import Comment
from praw.models import Submission
from praw.models.reddit.base import RedditBase
import re


class Tagging:
	@staticmethod
	def tag_comment(comment: Comment) -> str:
		try:
			if comment.submission.author.name == comment.author:
				return f'<|soopr u/{comment.author}|>{comment.body}<|eoopr|>'

			parent = comment.parent()
			parent_parent = parent.parent()
			if parent_parent.author.name == comment.author:
				return f'<|soocr u/{comment.author}|>{comment.body}<|eoocr|>'

		except Exception:
			return f'<|sor u/{comment.author}|>{comment.body}<|eor|>'

		return f'<|sor u/{comment.author}|>{comment.body}<|eor|>'

	@staticmethod
	def tag_submission(praw_thing: Submission):
		tagged_text = ""

		if praw_thing.is_self:
			tagged_text += "<|soss"
		else:
			tagged_text += "<|sols"

		tagged_text += f" r/{praw_thing.subreddit}|>"

		if praw_thing.is_self:
			selftext = praw_thing.selftext
			if hasattr(praw_thing, 'poll_data'):
				for option in praw_thing.poll_data.options:
					selftext += f" - {option.text}"
			tagged_text += f"<|sot|>{praw_thing.title}<|eot|><|sost|>{selftext}<|eost|>"

		else:
			tagged_text += f"<|sot|>{praw_thing.title}<|eot|><|sol|><|eol|>"

		return tagged_text

	@staticmethod
	def get_reply_tag(thing: RedditBase, bot_username: str) -> str:
		if isinstance(thing, Comment):
			if thing.submission:
				if thing.submission.author.name.lower() == bot_username.lower():
					return '<|soopr|>'
			if thing.parent():
				# if the parent's parent was by the author bot, use the own content tag
				if thing.parent().author.name.lower() == bot_username.lower():
					return '<|soocr|>'
		return '<|sor|>'

	@staticmethod
	def collate_tagged_comment_history(loop_thing: RedditBase, to_level=6) -> str:
		counter = 0
		prefix = ''

		while loop_thing and counter < to_level:

			if isinstance(loop_thing, Submission):
				tagged_text = Tagging.tag_submission(loop_thing)
				prefix = tagged_text + prefix
				break

			if isinstance(loop_thing, Comment):
				tagged_text = Tagging.tag_comment(loop_thing)
				prefix = tagged_text + prefix

				loop_thing = loop_thing.parent()

			counter += 1

		return prefix

	@staticmethod
	def remove_username_mentions_from_string(string: str, username: str) -> str:
		regex = re.compile(fr"u\/{username}(?!\|\>)", re.IGNORECASE)
		string = regex.sub('', string)
		return string
