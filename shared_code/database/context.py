import logging
import os
from typing import Union
from sqlalchemy import desc
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from shared_code.database.entities import TrackingSubmission, TrackingComment, Base, TrackingResponse


class Context:
	def __init__(self):
		self._user = os.environ['PsqlUser']
		self._password = os.environ['PsqlPassword']
		self._engine = create_engine(f"postgresql://{self._user}:{self._password}@localhost:5432/redditData", pool_size=32, max_overflow=-1)

	def get_session(self):
		return Session(self._engine)

	def close_and_dispose(self, session: Session):
		session.close()
		self._engine.dispose()

	@staticmethod
	def add(entity: Base, session: Session) -> Union[TrackingSubmission, TrackingComment, None]:
		try:
			existing_record = session.get(type(entity), entity.Id)
			if existing_record:
				logging.debug(f":: Record Exists for type {type(entity)} and Id {entity.Id}")
				return existing_record
			session.add(entity)
			session.commit()
			return None
		except Exception as e:
			logging.error(f":: An exception has occurred in method `Add` with message {e}")
		finally:
			pass

	@staticmethod
	def get_comments_for_processing(session: Session, limit=int):
		try:
			result = list(session.scalars(
				select(TrackingComment)
				.where(TrackingComment.Text == "")
				.order_by(desc(TrackingComment.CommentTimestamp))
				.limit(limit))
			)
			return result
		except Exception as e:
			logging.error(f":: An exception has occurred in method `Add` with message {e}")
		finally:
			pass

	def save(self, session: Session) -> None:
		try:
			session.commit()
		except Exception as e:
			logging.error(f":: An exception has occurred in method `Add` with message {e}")
		finally:
			self.close_and_dispose(session)
