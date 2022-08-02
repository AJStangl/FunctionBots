import base64
import json
import logging
import azure.functions as func
import datetime
from shared_code.database.table_record import TableRecord
from shared_code.models.bot_configuration import BotConfiguration

class Mapper:
	@staticmethod
	def table_to_dict(tableRecord: TableRecord) -> dict:
		return {
			"Id": tableRecord.Id,
			"RedditId": tableRecord.RedditId,
			"Subreddit":  tableRecord.Subreddit,
			"InputType":  tableRecord.InputType,
			"Author":  tableRecord.Author,
			"RespondingBot":  tableRecord.RespondingBot,
			"TextGenerationPrompt":  tableRecord.TextGenerationPrompt,
			"TextGenerationResponse":  tableRecord.TextGenerationResponse,
			"HasResponded":  tableRecord.HasResponded,
			"Status":  tableRecord.Status,
			"ReplyProbability":  tableRecord.ReplyProbability,
			"Url":  tableRecord.Url
		}

	@staticmethod
	def handle_message(message) -> BotConfiguration:
		try:
			message_json = message.get_body().decode('utf-8')
			incoming_message: BotConfiguration = json.loads(message_json, object_hook=lambda d: BotConfiguration(**d))
			return incoming_message
		except Exception:
			temp = message.handle_incoming_message(message)
			message_json = json.dumps(temp)
		incoming_message: BotConfiguration = json.loads(message_json, object_hook=lambda d: BotConfiguration(**d))
		return incoming_message

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

	@staticmethod
	def chain_listing_generators(*iterables):
		for it in iterables:
			for element in it:
				if element is None:
					break
				else:
					yield element