import logging
import os
import time
from datetime import datetime
from typing import Optional

import azure.functions as func
from asyncpraw.models import Redditor, Subreddit, Comment, Submission

from shared_code.database.table_record import TableRecord
from shared_code.helpers.mapping_models import Mapper
from shared_code.helpers.merge_async_iterator import MergeAsyncIterator
from shared_code.models.bot_configuration import BotConfiguration
from shared_code.services.service_container import ServiceContainer


class InvokePollingService(ServiceContainer):
	def __init__(self):
		super().__init__()

	async def invoke_reddit_polling(self, message: func.QueueMessage) -> None:
		logging.info(f":: Starting invoke_reddit_polling")

		try:
			incoming_message: BotConfiguration = Mapper.handle_message(message)

			bot_name: str = incoming_message.Name

			self.set_reddit_instance(bot_name)

			try:
				user: Redditor = await self.reddit_instance.user.me()
			except Exception as e:
				logging.error(f"::Error Getting User...Exiting -- {e}")
				return None

			subs: str = self.reddit_helper.get_subs_from_configuration(bot_name)

			subreddit: Subreddit = await self.reddit_instance.subreddit(subs)

			comment_stream = subreddit.stream.comments()
			submission_stream = subreddit.stream.submissions()

			start_time = time.time()
			time_out_for_iteration: float = float(os.environ["TimeoutForSearchIterator"])
			logging.info(f":: Processing the Data For {time_out_for_iteration} seconds")
			async for praw_item in MergeAsyncIterator(submission_stream, comment_stream, time_out=time_out_for_iteration):
				try:
					if praw_item is None:
						break
					if isinstance(praw_item, Comment):
						logging.info(f":: Handling {type(praw_item).__name__} {praw_item} from stream")
						comment: Comment = praw_item
						await self.insert_comment_to_table(comment, user)

					if isinstance(praw_item, Submission):
						logging.debug(f":: Handling {type(praw_item).__name__} {praw_item} from stream")
						submission: Submission = praw_item
						await self.insert_submission_to_table(submission, user)
				except Exception as e:
					logging.error(f":: An exception has occurred while iterating incoming data with error: {e}")
					break

			end_time = time.time()
			duration = round(end_time - start_time, 1)

			logging.info(f":: Total Duration for Processing: {duration}")
			logging.info(f":: Polling Method Complete For {bot_name}")
			return None
		finally:
			await self.close_reddit_instance()

	async def insert_submission_to_table(self, submission: Submission, user: Redditor) -> Optional[TableRecord]:
		existing = self.repository.get_entity_by_id(f"{submission.id}|{user.name}")
		if existing:
			return existing
		user = await self.reddit_instance.user.me()
		probability: int = await self.reply_logic.calculate_reply_probability(submission, user)
		if user.name == getattr(submission.author, 'name', ''):
			probability = 0

		mapped_input: TableRecord = self.table_helper.map_base_to_message(
			reddit_id=submission.id,
			sub_reddit=submission.subreddit.display_name,
			input_type="Submission",
			submitted_date=datetime.fromtimestamp(submission.created_utc),
			author=getattr(submission.author, 'name', ''),
			responding_bot=user.name,
			reply_probability=probability,
			url=submission.url
		)

		entity = self.repository.create_if_not_exist(mapped_input)
		if entity:
			logging.info(f":: Inserting Record submission {submission.id} with probability {probability} for {user.name}")
			return entity

	async def insert_comment_to_table(self, comment: Comment, user: Redditor) -> Optional[TableRecord]:
		existing = self.repository.get_entity_by_id(f"{comment.id}|{user.name}")
		if existing:
			return existing
		try:
			user = await self.reddit_instance.user.me()
			probability: int = await self.reply_logic.calculate_reply_probability(comment, user)
		except Exception as e:
			logging.error(f":: Error Attempting Probability Calculation {e}")
			return None
		try:
			pass
		except Exception as e:
			logging.error(f":: Error Attempting To Get Submission for entity {e}")
			return None

		logging.debug(f":: Mapping Input {comment.id} for {comment.subreddit.display_name}")
		mapped_input: TableRecord = Mapper.map_base_to_message(
			reddit_id=comment.id,
			sub_reddit=comment.subreddit.display_name,
			input_type="Comment",
			submitted_date=datetime.fromtimestamp(comment.created_utc),
			author=getattr(comment.author, 'name', ''),
			responding_bot=user.name,
			reply_probability=probability,
			url=comment.permalink)

		entity = self.repository.create_if_not_exist(mapped_input)
		if entity:
			logging.info(f":: Inserting Record comment {comment.id} with probability {probability} for {user.name}")
			return entity
