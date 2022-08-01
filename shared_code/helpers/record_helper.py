import base64
import datetime
import json
import logging

import azure.functions as func
from shared_code.database.table_record import TableRecord


class TableHelper:
	@staticmethod
	def map_base_to_message(reddit_id: str, sub_reddit: str, input_type: str, submitted_date: datetime.datetime, author: str, responding_bot: str, reply_probability: int, url: str) -> TableRecord:
		set_id = f"{reddit_id}|{responding_bot}"
		record = TableRecord()
		record.Id = set_id
		record.RedditId = reddit_id
		record.Subreddit = sub_reddit
		record.InputType = input_type
		record.ContentDateSubmitted = submitted_date
		record.Author = author
		record.RespondingBot = responding_bot
		record.TextGenerationPrompt = ""
		record.TextGenerationResponse = ""
		record.HasResponded = False
		record.Status = 0
		record.ReplyProbability = reply_probability
		record.DateTimeSubmitted = None
		record.Url = url
		return record

	@staticmethod
	def handle_incoming_message(message) -> TableRecord:
		try:
			incoming_message: TableRecord = json.loads(base64.b64decode(message.content))
			return incoming_message
		except Exception as e:
			logging.debug(f"{e}")
			incoming_message: TableRecord = json.loads(message.content)
			return incoming_message

	@staticmethod
	def handle_fucking_bullshit(message: func.QueueMessage) -> TableRecord:
		try:
			incoming_message: TableRecord = json.loads(json.dumps(message.get_json()))
			return incoming_message
		except Exception as e:
			logging.info(f":: Fucking bullshit man {e}")

	@staticmethod
	def handle_message_generic(message: func.QueueMessage) -> dict:
		try:
			return json.loads(json.dumps(message.get_json()))
		except Exception as e:
			return json.loads(base64.b64decode(message.get_body()))

