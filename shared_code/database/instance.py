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
	Author = Column(String)
	RespondingBot = Column(String)
	TextGenerationPrompt = Column(String)
	TextGenerationResponse = Column(String)
	HasResponded = Column(Boolean)
	Status = Column(Integer)

	def as_dict(self):
		return {c.name: getattr(self, c.name) for c in self.__table__.columns}

engine = create_engine('sqlite:///shared_code/database/bot-db.sqlite3', echo=True)

Base.metadata.create_all(engine)



