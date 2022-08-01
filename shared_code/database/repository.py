import logging
import os

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy import desc
from shared_code.database.table_record import TableRecord
from sqlalchemy import create_engine

class DataRepository:
	def __init__(self):
		self._user = os.environ['PsqlUser']
		self._password = os.environ['PsqlPassword']
		self._engine = create_engine(f"postgresql://{self._user}:{self._password}@localhost:5432/redditData", pool_size=32, max_overflow=-1)

	def get_session(self):
		return Session(self._engine)

	def close_and_dispose(self, session: Session):
		session.close()
		self._engine.dispose()

	def create_if_not_exist(self, record) -> TableRecord:
		session = Session(self._engine)
		try:
			entity = session.get(TableRecord, record.Id)
			if entity:
				return None
			else:
				session.add(record)
				session.commit()
				return record
		except Exception as e:
			logging.info(f":: {e}")
		finally:
			session.close()
			self._engine.dispose()

	def search_for_unsent_replies(self, bot_name: str):
		session = Session(self._engine)
		try:
			entity = session.execute(
				select(TableRecord)
					.where(TableRecord.Status == 1)
					.where(TableRecord.TextGenerationResponse != '')
					.where(TableRecord.HasResponded is False)
					.where(TableRecord.RespondingBot == bot_name)
					.order_by(desc(TableRecord.ContentDateSubmitted)))\
				.all()
			return entity
		finally:
			session.close()
			self._engine.dispose()

	def search_for_pending(self, input_type: str, bot_name: str, limit: int = 100):
		session = Session(self._engine)
		try:
			entity = session.execute(
				select(TableRecord)
					.where(TableRecord.Status == 0)
					.where(TableRecord.ReplyProbability > 0)
					.where(TableRecord.InputType == input_type)
					.where(TableRecord.RespondingBot == bot_name)
					.limit(limit)
					.order_by(desc(TableRecord.ContentDateSubmitted)))\
				.all()
			return entity
		finally:
			session.close()
			session.close_all()
			self._engine.dispose()

	def get_by_id_with_session(self, session: Session, id: str) -> TableRecord:
		return session.get(TableRecord, id)


	def get_entity_by_id(self, Id: str) -> TableRecord:
		session = Session(self._engine)
		try:
			entity = session.get(TableRecord, Id)
			return entity
		finally:
			session.close()
			self._engine.dispose()
