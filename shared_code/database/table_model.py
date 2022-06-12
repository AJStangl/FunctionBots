import base64
import json

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TableRecord(Base):
	__tablename__ = "BotTracking"
	Id = Column(String, primary_key=True)
	RedditId = Column(String)
	Subreddit = Column(String)
	InputType = Column(String)
	ContentDateSubmitted = Column(Integer)
	Author = Column(String)
	RespondingBot = Column(String)
	TextGenerationPrompt = Column(String)
	TextGenerationResponse = Column(String)
	HasResponded = Column(Boolean)
	Status = Column(Integer)

	def as_dict(self):
		return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class TableHelper:
	@staticmethod
	def map_base_to_message(reddit_id: str, sub_reddit: str, input_type: str, submitted_date: int, author: str, responding_bot: str) -> TableRecord:
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
		return record

	@staticmethod
	def handle_incoming_message(message) -> TableRecord:
		try:
			incoming_message: TableRecord = json.loads(base64.b64decode(message.content))
			return incoming_message
		except Exception:
			incoming_message: TableRecord = json.loads(message.content)
			return incoming_message


