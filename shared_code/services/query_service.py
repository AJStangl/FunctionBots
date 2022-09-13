import json
import logging
import os
import random
from datetime import datetime, timedelta
from typing import Optional

from asyncpraw.models import Comment, Submission
from azure.storage.queue import TextBase64EncodePolicy
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared_code.database.table_record import TableRecord
from shared_code.helpers.mapping_models import Mapper
from shared_code.models.bot_configuration import BotConfiguration
from shared_code.services.service_container import ServiceContainer


class QueryService(ServiceContainer):
	def __init__(self):
		super().__init__()
		self.message_live_in_hours = 60 * 60 * 8
		self.all_workers: [str] = ["worker-1", "worker-2", "worker-3"]

	async def invoke_data_query(self, message) -> None:
		logging.info(f":: Starting QueryService invoke_data_query")
		try:
			bot_config: BotConfiguration = Mapper.handle_message(message)
			bot_name = bot_config.Name
			self.set_reddit_instance(bot_name)

			pending_submissions = self.repository.search_for_pending("Submission", bot_name, limit=30)
			logging.info(f":: Handling submissions for {bot_name}")
			for record in pending_submissions:
				await self.handle_incoming_record(record)

			logging.info(f":: Submission Handling Complete for {bot_name}")
			logging.info(f":: Fetching latest Comments For {bot_name}")
			pending_comments = self.repository.search_for_pending("Comment", bot_name, limit=1000)

			end_time = datetime.now() + timedelta(minutes=10)
			logging.info(f":: Handling comments for {bot_name} - Attempting for {end_time}...")
			for record in pending_comments:
				if end_time < datetime.now():
					logging.info(":: Max time exceeded for processing comments...")
					break
				await self.handle_incoming_record(record)
			logging.info(f":: Submission comments Complete for {bot_name}")

			return None

		finally:
			if self.reddit_instance:
				await self.close_reddit_instance()

	async def handle_incoming_record(self, record):
		worker: str = random.choice(self.all_workers)
		queue = self.queue_proxy.service.get_queue_client(worker, message_encode_policy=TextBase64EncodePolicy())
		session: Session = self.repository.get_session()
		try:
			record = record['TableRecord']
			entity = self.repository.get_by_id_with_session(session, record.Id)
			entity.Status = 1
			session.commit()

			processed = entity.TextGenerationPrompt

			if processed == "" or processed is None:
				logging.info(f":: starting input processing on {entity.Id}")
				try:
					processed = await self.process_input(record)
					if processed is None or processed == "":
						logging.info(f":: Message Has nothing processed for record {record.Id}")
						return None
				except Exception as e:
					logging.error(f":: Exception occurred while process_input {e}")
					return None

			entity.TextGenerationPrompt = processed
			self.repository.update_comments_by_reddit_id(record.RedditId, processed, session)
			max_probability = int(os.environ["MaxProbability"])
			reply_probability_target: int = random.randint(0, max_probability)
			if record.InputType == "Submission":
				session.commit()
				logging.info(f":: Sending {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation to {record.Subreddit} on {worker}")
				foo = Mapper.table_to_dict(entity)
				queue.send_message(json.dumps(foo), time_to_live=self.message_live_in_hours)
				return None

			if record.ReplyProbability >= max_probability and record.InputType == "Comment":
				session.commit()
				logging.info(f":: Sending {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation to {record.Subreddit} on {worker}")
				foo = Mapper.table_to_dict(entity)
				queue.send_message(json.dumps(foo), time_to_live=self.message_live_in_hours)
				return None

			else:
				logging.debug(f":: Ignoring {record.InputType} for {record.RespondingBot} has a Probability of {record.ReplyProbability} but needs {reply_probability_target}")
				entity.Status = 2
				session.commit()
				return None
		finally:
			queue.close()
			session.close()

	async def process_input(self, record: TableRecord) -> Optional[str]:
		if record.InputType == "Submission":
			thing_submission: Submission = await self.reddit_instance.submission(id=record.RedditId, fetch=True)
			if thing_submission is None:
				return None
			try:
				await thing_submission.load()
			except Exception as e:
				logging.error(f":: Error loading comment returning None {e}")
				return None

			try:
				history: str = await self.tagging.collate_tagged_comment_history(thing_submission)
			except Exception as e:
				logging.error(f": error Attempting to get history. Returning None {e}")
				return None

			cleaned_history: str = self.tagging.remove_username_mentions_from_string(history, record.RespondingBot)

			try:
				reply_start_tag: str = await self.tagging.get_reply_tag(thing_submission)
			except Exception as e:
				logging.info(f":: Failed to get reply tag with error {e}")
				return None

			prompt: str = cleaned_history + reply_start_tag

			return prompt

		if record.InputType == "Comment":
			try:
				thing_comment: Comment = await self.reddit_instance.comment(id=record.RedditId, fetch=True)
			except Exception as e:
				logging.error(f":: Failed to load comment {e}")
				return None

			if thing_comment is None:
				return None

			try:
				await thing_comment.load()
			except Exception as e:
				logging.error(f":: Failed to load comment {e}")
				return None

			history: str = await self.tagging.collate_tagged_comment_history(thing_comment)
			cleaned_history: str = self.tagging.remove_username_mentions_from_string(history, record.RespondingBot)
			reply_start_tag: str = await self.tagging.get_reply_tag(thing_comment)
			prompt: str = cleaned_history + reply_start_tag
			return prompt