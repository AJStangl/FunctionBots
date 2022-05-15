import logging
import json
import typing

import azure.functions as func
from azure.functions import QueueMessage

from shared_code.models.praw_content_message import PrawQueueMessage
from shared_code.models.table_data import InputTableRecord


def main(messageIn: QueueMessage, message: func.Out[str], msg: func.Out[typing.List[str]]) -> None:
	logging.info(f":: Message Obtained For Processing")

	json_body = messageIn.get_json()

	table_record = process_message(json_body)

	output = table_record.to_dictionary()

	message.set(json.dumps(output))

	logging.info(f":: New Entry Entered for {table_record.id}")

	msg.set([json.dumps(output)])

	return


def process_message(queue_message: dict[str]) -> InputTableRecord:
	received_message = PrawQueueMessage.from_json(queue_message)
	table_record = InputTableRecord()
	split_id = received_message.source_name.split("_")
	table_record.partition_key = received_message.get_partition_key()
	table_record.row_key = split_id[1]
	table_record.id = split_id[1]
	table_record.name_id = received_message.source_name
	table_record.subreddit = received_message.subreddit
	table_record.input_type = received_message.input_type
	table_record.content_date_submitted_utc = int(received_message.created_utc)
	table_record.author = received_message.author
	table_record.responding_bot = received_message.bot_username
	table_record.text_generation_prompt = None
	table_record.text_generation_response = None
	table_record.has_responded = False
	return table_record
