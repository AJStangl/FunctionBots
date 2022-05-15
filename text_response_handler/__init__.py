import json
import logging
from typing import Optional

import azure.functions as func
import ftfy
import codecs
from shared_code.storage_proxies.table_proxy import TableServiceProxy
from shared_code.helpers.reddit_helper import RedditHelper

def main(message: func.QueueMessage) -> None:

	service = TableServiceProxy().service
	client = service.get_table_client("tracking")
	helper = RedditHelper()

	message_json = message.get_body().decode('utf-8')

	message_json = json.loads(message_json)

	partition_key = message_json["PartitionKey"]

	row_key = message_json["RowKey"]

	split_key = partition_key.split("|")

	bot_name = split_key[1]

	response_to_id = message_json['id']

	prompt = message_json["text_generation_prompt"]
	response = message_json["text_generation_response"]

	instance = helper.get_praw_instance(bot_name=bot_name)

	foo = extract_reply_from_generated_text(prompt, response)

	if message_json["input_type"] == "comments":
		logging.info(f":: Replying to Comment - {response_to_id}")
		comment_instance = instance.comment(id=response_to_id)
		comment_instance.reply(foo)

	else:
		logging.info(f":: Replying to Submission - {response_to_id}")
		submission_instance = instance.submission(id=response_to_id)
		foo = extract_reply_from_generated_text(prompt, response)
		submission_instance.reply(foo)

	logging.info(f":: Setting entity to Read - {partition_key}")
	entity = client.get_entity(partition_key, row_key)

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
		logging.info("Truncate string not found")
		return None

	# extract the text from between the prompt and the truncate point
	reply_body = generated_text[len(prompt):index_of_truncate]
	if reply_body:
		return reply_body

	# Return nothing
	return None


def decode_generated_text(text):
	return ftfy.fix_text(codecs.decode(text, "unicode_escape"))

