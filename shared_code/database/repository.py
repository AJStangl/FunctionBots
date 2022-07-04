import logging
import os

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy import desc
from shared_code.database.instance import engine, TableRecord


class DataRepository:
	def __init__(self):
		self._user = os.environ['PsqlUser']
		self._password = os.environ['PsqlPassword']

	def create_entry(self, record: TableRecord):
		session = Session(engine)
		try:
			session.add(record)
			session.commit()
		except Exception as e:
			logging.info(f":: {e}")
		finally:
			session.close()

	def create_if_not_exist(self, record) -> TableRecord:
		session = Session(engine)
		try:
			entity = session.get(TableRecord, record.Id)
			if entity:
				return entity
			else:
				session.add(record)
				session.commit()
				return record
		except Exception as e:
			logging.info(f":: {e}")
		finally:
			session.close()

	def search_for_pending(self, input_type: str, bot_name: str):
		session = Session(engine)
		try:
			entity = session.execute(
				select(TableRecord)
					.where(TableRecord.Status == 0)
					.where(TableRecord.InputType == input_type)
					.where(TableRecord.RespondingBot == bot_name)
					.limit(10)
					.order_by(desc(TableRecord.ContentDateSubmitted)))\
				.all()
			return entity
		finally:
			session.close()

	def update_entity(self, entity):
		session = Session(engine)
		try:
			props = entity.as_dict()
			session.query(TableRecord). \
				filter(TableRecord.Id == entity.Id). \
				update(props)
			session.commit()
		finally:
			session.close()

	def get_entity_by_id(self, Id: str) -> TableRecord:
		session = Session(engine)
		try:
			entity = session.get(TableRecord, Id)
			return entity
		finally:
			session.close()
