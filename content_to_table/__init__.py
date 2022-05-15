import logging
import json
import typing

import azure.functions as func
from azure.functions import QueueMessage

from shared_code.models.praw_content_message import PrawQueueMessage
from shared_code.models.table_data import InputTableRecord
from shared_code.storage_proxies.table_proxy import TableServiceProxy


def main(messageIn: QueueMessage, msg: func.Out[str]) -> None:
	logging.info(f":: Message Obtained For Processing")

	service = TableServiceProxy().service
	client = service.get_table_client("tracking")

	json_body = messageIn.get_json()

	split_name = json_body["source_name"].split("_")
	#TODO: Fix this
	# f"{self.subreddit}|{self.bot_username}"
	# record_dict = {
	# 	'PartitionKey': self.partition_key,
	# 	'RowKey': split_name[1],
	# 	'id': self.id,
	# 	'name_id': self.name_id,
	# 	'subreddit': self.subreddit,
	# 	'input_type': self.input_type,
	# 	'content_date_submitted_utc': self.content_date_submitted_utc,
	# 	'author': self.author,
	# 	'responding_bot': self.responding_bot,
	# 	'text_generation_prompt': self.text_generation_prompt,
	# 	'text_generation_response': self.text_generation_response,
	# 	'has_responded': self.has_responded
	# }

	table_record = process_message(json_body)

	if table_record["author"] == table_record["responding_bot"]:
		logging.info(":: Skipping Rely To Self")
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
