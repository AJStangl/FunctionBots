import json
import logging
from types import SimpleNamespace

import azure.functions as func
from praw.models import Submission
from praw.models.reddit.base import RedditBase
from praw.reddit import Comment

from shared_code.helpers.reddit_helper import RedditHelper
from shared_code.models.table_data import InputTableRecord


def main(message: func.QueueMessage, promptMessage: func.Out[str]) -> None:

	message_json = message.get_body().decode('utf-8')

	incoming_message = json.loads(message_json, object_hook=lambda d: SimpleNamespace(**d))

	prompt = process_input(incoming_message)

	prompt_message = map_message(incoming_message, prompt)

	promptMessage.set(json.dumps(prompt_message))


def map_message(message_record: SimpleNamespace, prompt: str) -> dict[str]:
	return {
		"partition_key": message_record.PartitionKey,
		"row_key": message_record.RowKey,
		"text_generation_prompt": prompt
	}


def get_reply_tag(thing: RedditBase, bot_username: str) -> str:
	# Need this praw_Comment check for message replies
	if isinstance(thing, Comment):
		if thing.submission:
			# The submission was by the bot so use special tag
			if thing.submission.author.name.lower() == bot_username.lower():
				return '<|soopr|>'
		if thing.parent():
			# if the parent's parent was by the author bot, use the own content tag
			if thing.parent().author.name.lower() == bot_username.lower():
				return '<|soocr|>'

	return '<|sor|>'


def process_input(incoming_message: InputTableRecord) -> str:
	helper = RedditHelper()
	instance = helper.get_praw_instance(incoming_message.responding_bot)

	if incoming_message.input_type == "Submission":
		logging.info(":: In Submission")
		thing = instance.submission(id=incoming_message.id)
		history = collate_tagged_comment_history(thing)
	else:
		thing = instance.comment(id=incoming_message.id)
		history = collate_tagged_comment_history(thing)

	cleaned_history = remove_username_mentions_from_string(history, incoming_message.responding_bot)
	reply_start_tag = get_reply_tag(thing, incoming_message.responding_bot)
	prompt = cleaned_history + reply_start_tag
	return prompt


def collate_tagged_comment_history(loop_thing: RedditBase, to_level=6) -> str:
	counter = 0
	prefix = ''

	while loop_thing and counter < to_level:

		if isinstance(loop_thing, Submission):
			tagged_text = tag_submission(loop_thing)
			prefix = tagged_text + prefix
			break

		if isinstance(loop_thing, Comment):
			tagged_text = tag_comment(loop_thing)
			prefix = tagged_text + prefix

			loop_thing = loop_thing.parent()

		counter += 1

	return prefix


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


def remove_username_mentions_from_string(string: str, username: str) -> str:
	import re
	regex = re.compile(fr"u\/{username}(?!\|\>)", re.IGNORECASE)
	string = regex.sub('', string)
	return string
