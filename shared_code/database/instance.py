import base64
import json
import os
from sqlalchemy import create_engine
from sqlalchemy import create_engine, ForeignKey
from sqlalchemy import Column, Date, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Boolean
from sqlalchemy.orm import declarative_base
import azure.functions as func
# TODO: For cloud deployment we may consider using PSQL.
# import psycopg2
# conn_string = "host='localhost' dbname='redditData' user='postgres' password='guitar!01'"
# conn = psycopg2.connect(conn_string)
# user = os.environ['PsqlUser']
# password = os.environ['PsqlPassword']
# engine = create_engine(f"postgresql://{user}:{password}@localhost:5432/redditData", pool_size=30, max_overflow=-1)

Base = declarative_base()

class TableRecord(Base):
	__tablename__ = "BotTracking"
	Id = Column(String, primary_key=True)
	RedditId = Column(String)
	Subreddit = Column(String)
	InputType = Column(String)
	ContentDateSubmitted = Column(Integer)
	TimeInHours = Column(Integer)
	Author = Column(String)
	RespondingBot = Column(String)
	TextGenerationPrompt = Column(String)
	TextGenerationResponse = Column(String)
	HasResponded = Column(Boolean)
	Status = Column(Integer)

	def as_dict(self):
		return {c.name: getattr(self, c.name) for c in self.__table__.columns}

engine = create_engine('sqlite:///shared_code/database/bot-db.sqlite3?check_same_thread=False', echo=False)

Base.metadata.create_all(engine)


class TableHelper:
	@staticmethod
	def map_base_to_message(reddit_id: str, sub_reddit: str, input_type: str, submitted_date: int, author: str, responding_bot: str, time_in_hours: int) -> TableRecord:
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

