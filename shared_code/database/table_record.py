from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TableRecord:
	pass


class TableRecord(Base):
	__tablename__ = "BotTracking"
	Id = Column(String, primary_key=True)
	RedditId = Column(String)
	Subreddit = Column(String)
	InputType = Column(String)
	ContentDateSubmitted = Column(TIMESTAMP)
	RepliedAt = Column(TIMESTAMP)
	Author = Column(String)
	RespondingBot = Column(String)
	TextGenerationPrompt = Column(String)
	TextGenerationResponse = Column(String)
	HasResponded = Column(Boolean)
	Status = Column(Integer)
	ReplyProbability = Column(Integer)
	Url = Column(String)

