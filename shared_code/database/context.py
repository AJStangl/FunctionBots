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

	def add(self, entity: Base, session: Session) -> Union[TrackingSubmission, TrackingComment, None]:
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
	def add_with_tracking(entity: Base, trackingResponse: TrackingResponse, session: Session) -> Union[TrackingSubmission, TrackingComment, None]:
		try:
			existing_record = session.get(type(entity), entity.Id)
			if existing_record:
				logging.debug(f":: Record Exists for type {type(entity)} and Id {entity.Id}")
				return existing_record
			session.add(entity)
			session.commit()
			return existing_record
		except Exception as e:
			logging.error(f":: An exception has occurred in method `Add` with message {e}")
		finally:
			pass

	def get_comments_for_processing(self, session: Session, limit=int):
		try:
			result = list(session.scalars(
				select(TrackingComment)
				.where(TrackingComment.Text == "")
				.order_by(desc(TrackingComment.DateCreated))
				.limit(limit))
			)
			return result
		except Exception as e:
			logging.error(f":: An exception has occurred in method `Add` with message {e}")
		finally:
			pass

	def get_items_ready_for_text_generation(self, bot_name: str, session: Session, limit=int):
		try:
			statement = select(TrackingResponse)\
				.join(TrackingComment)\
				.where(TrackingResponse.BotName == bot_name)\
				.where(TrackingComment.Author != bot_name)\
				.where(TrackingResponse.HasResponded == False)\
				.where(TrackingComment.Text != '')\
				.order_by(desc(TrackingComment.DateCreated))\
				.limit(limit)
# 			select *
# 			from
# 			"TrackingResponse"
# 			join
# 			"TrackingComment"
# 			comment
# 			on
# 			"TrackingResponse".
# 			"CommentId" = comment.
# 			"Id"
# 		where
# 		"TrackingResponse".
# 		"BotName" = 'PabloBot-GPT2'
# 		and comment.
# 		"Author" != 'PabloBot-GPT2'
# 		and "TrackingResponse".
# 		"HasResponded" = false
# 		and comment.
# 		"Text" != ''
#
#
# order
# by
# comment.
# "CommentTimestamp"
# desc;
			print(statement)

			return list(session.scalars(statement))
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
