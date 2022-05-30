import json
import logging
from typing import Optional

import azure.functions as func
import ftfy
import codecs
import datetime

from shared_code.models.table_data import TableRecord
from shared_code.storage_proxies.table_proxy import TableServiceProxy
from shared_code.helpers.reddit_helper import RedditHelper

def main(message: func.QueueMessage) -> None:

	logging.debug(f":: Trigger For Reply Handler Generation called at {datetime.date.today()}")

	service = TableServiceProxy().service
	client = service.get_table_client("tracking")
	helper = RedditHelper()

	message_json = message.get_body().decode('utf-8')

	incoming_message = json.loads(message_json, object_hook=lambda d: TableRecord(**d))

	instance = helper.get_praw_instance(bot_name=incoming_message.responding_bot)

	prompt = incoming_message.text_generation_prompt

	response = incoming_message.text_generation_response

	reply = extract_reply_from_generated_text(prompt, response)

	entity = client.get_entity(incoming_message.PartitionKey, incoming_message.RowKey)

	if reply is None:
		entity["has_responded"] = False
		client.update_entity(entity)
		return None

	if incoming_message.input_type == "Comment":
		logging.debug(f":: Replying to Comment From {incoming_message.author} in {incoming_message.subreddit}")
		comment_instance = instance.comment(id=incoming_message.id)
		comment_instance.reply(reply)

	else:
		logging.debug(f":: Replying to Submission From {incoming_message.author} in {incoming_message.subreddit}")
		submission_instance = instance.submission(id=incoming_message.id)
		submission_instance.reply(reply)

	entity["has_responded"] = True
	client.update_entity(entity)
	return None


def extract_reply_from_generated_text(prompt, generated_text) -> Optional[str]:
	end_tag = '<|'

	index_of_truncate = generated_text.find(end_tag, len(prompt))

	if index_of_truncate == -1:
		index_of_truncate = generated_text.rfind("\\n")

	if index_of_truncate == -1:
		index_of_truncate = generated_text.find("!!!!")

	if index_of_truncate == -1:
		logging.debug(":: String Is EmptyTruncate string not found")
		return None

	# extract the text from between the prompt and the truncate point
	reply_body = generated_text[len(prompt):index_of_truncate]
	if reply_body:
		return reply_body

	# Return nothing
	return None


def decode_generated_text(text):
	return ftfy.fix_text(codecs.decode(text, "unicode_escape"))

