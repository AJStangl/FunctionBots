import base64
import datetime
import json
import azure.functions as func
from shared_code.database.instance import TableRecord


class TableHelper:
	@staticmethod
	def map_base_to_message(reddit_id: str, sub_reddit: str, input_type: str, submitted_date: int, author: str,
							responding_bot: str, time_in_hours: int, reply_probability: int) -> TableRecord:
		set_id = f"{reddit_id}|{responding_bot}"
		record = TableRecord()
		record.Id = set_id
		record.RedditId = reddit_id
		record.Subreddit = sub_reddit
		record.InputType = input_type
		record.ContentDateSubmitted = submitted_date
		record.TimeInHours = time_in_hours
		record.Author = author
		record.RespondingBot = responding_bot
		record.TextGenerationPrompt = ""
		record.TextGenerationResponse = ""
		record.HasResponded = False
		record.Status = 0
		record.ReplyProbability = reply_probability
		record.DateTimeCreated = str(datetime.datetime.now())
		record.DateTimeSubmitted = None
		return record

	@staticmethod
	def handle_incoming_message(message) -> TableRecord:
		try:
			incoming_message: TableRecord = json.loads(base64.b64decode(message.content))
			return incoming_message
		except Exception:
			incoming_message: TableRecord = json.loads(message.content)
			return incoming_message

	@staticmethod
	def handle_fucking_bullshit(message: func.QueueMessage) -> TableRecord:
		try:
			incoming_message: TableRecord = json.loads(json.dumps(message.get_json()))
			return incoming_message
		except:
			print("Fucking bullshit man")
