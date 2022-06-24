import logging
import os

from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from shared_code.database.instance import engine
from shared_code.database.table_model import TableRecord


class DataRepository:
	def __init__(self):
		self._user = os.environ['PsqlUser']
		self._password = os.environ['PsqlPassword']

	def create_entry(self, record: TableRecord):
		try:
			session = Session(engine)
			session.add(record)
			session.commit()
			session.close()
		except Exception as e:
			logging.info(f":: {e}")

	def create_if_not_exist(self, record) -> TableRecord:
		session = Session(engine)
		entity = session.get(TableRecord, record.Id)
		if entity:
			session.close()
			return entity

		else:
			self.create_entry(record)
			return record

	def search_for_pending(self, input_type: str, bot_name: str):
		session = Session(engine)
		entity = session.execute(
			select(TableRecord)
				.where(TableRecord.TextGenerationPrompt == "")
				.where(TableRecord.Status == 0)
				.where(TableRecord.InputType == input_type)
				.order_by(TableRecord.ContentDateSubmitted))\
			.all()
		session.close()
		return entity

	def update_entity(self, entity):
		session = Session(engine)
		props = entity.as_dict()
		session.query(TableRecord). \
			filter(TableRecord.Id == entity.Id). \
			update(props)
		session.commit()
		session.close()

	def get_entity_by_id(self, Id: str) -> TableRecord:
		session = Session(engine)
		entity = session.get(TableRecord, Id)
		session.close()
		return entity
