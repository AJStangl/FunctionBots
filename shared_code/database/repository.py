from sqlalchemy import select
from sqlalchemy.orm import Session

from shared_code.database.instance import engine
from shared_code.database.table_model import TableRecord


class DataRepository:
	def __init__(self):
		pass

	def create_entry(self, record: TableRecord):
		with Session(engine) as session:
			session.add(record)
			session.commit()

	def create_if_not_exist(self, record) -> TableRecord:
		with Session(engine) as session:
			entity = session.get(TableRecord, record.Id)
			if entity:
				return entity
			else:
				self.create_entry(record)
				return record

	def search_for_pending(self, input_type: str):
		with Session(engine) as session:
			return session.execute(
				select(TableRecord)
					.where(TableRecord.TextGenerationPrompt == "")
					.where(TableRecord.Status == 0)
					.where(TableRecord.InputType == input_type)
					.order_by(TableRecord.ContentDateSubmitted.desc())).scalars().all()

	def update_entity(self, entity):
		with Session(engine) as session:
			props = entity.as_dict()
			session.query(TableRecord). \
				filter(TableRecord.Id == entity.Id). \
				update(props)
			session.commit()

	def get_entity_by_id(self, Id: str) -> TableRecord:
		with Session(engine) as session:
			return session.get(TableRecord, Id)
