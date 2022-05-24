import json
import logging
import datetime
from typing import Optional
import azure.functions as func

from shared_code.helpers.reddit_helper import RedditHelper
from shared_code.models.table_data import TableRecord
from shared_code.helpers.tagging import Tagging

def main(message: func.QueueMessage, promptMessage: func.Out[str]) -> None:

	logging.info(f":: Trigger For Text Prompt Extraction called at {datetime.date.today()}")

	message_json = message.get_body().decode('utf-8')

	incoming_message = json.loads(message_json, object_hook=lambda d: TableRecord(**d))

	incoming_message.text_generation_prompt = process_input(incoming_message)

	if incoming_message.text_generation_prompt is not None:
		promptMessage.set(incoming_message.json)

def process_input(incoming_message: TableRecord) -> Optional[str]:
	helper = RedditHelper()
	instance = helper.get_praw_instance(incoming_message.responding_bot)

	if incoming_message.input_type == "Submission":
		thing = instance.submission(id=incoming_message.id)
		history = Tagging.collate_tagged_comment_history(thing)

	if incoming_message.input_type == "Comment":
		thing = instance.comment(id=incoming_message.id)
		history = Tagging.collate_tagged_comment_history(thing)
	else:
		return None

	cleaned_history = Tagging.remove_username_mentions_from_string(history, incoming_message.responding_bot)
	reply_start_tag = Tagging.get_reply_tag(thing, incoming_message.responding_bot)
	prompt = cleaned_history + reply_start_tag
	return prompt