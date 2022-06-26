import os

import psycopg2
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base

user = os.environ['PsqlUser']
password = os.environ['PsqlPassword']
conn_string = f"host='localhost' dbname='redditData' user='{user}' password='{password}'"
conn = psycopg2.connect(conn_string)

Base = declarative_base()

class TableRecord(Base):
	__tablename__ = "BotTracking"
	Id = Column(String, primary_key=True)
	DateTimeCreated = Column(String)
	DateTimeSubmitted = Column(String)
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
	ReplyProbability = Column(Integer)
	Url = Column(String)

	def as_dict(self):
		return {c.name: getattr(self, c.name) for c in self.__table__.columns}

engine = create_engine(f"postgresql://{user}:{password}@localhost:5432/redditData", pool_size=30, max_overflow=-1)

Base.metadata.create_all(engine)




