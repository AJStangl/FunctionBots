import datetime
import json
import logging
import os
import random
import time
from datetime import datetime, timedelta
from typing import Optional

import azure.functions as func
from asyncpraw.models import Submission, Subreddit
from asyncpraw.reddit import Redditor, Comment
from azure.storage.queue import TextBase64EncodePolicy
from sqlalchemy.orm import Session

from shared_code.database.table_record import TableRecord
from shared_code.helpers.merge_async_iterator import MergeAsyncIterator
from shared_code.helpers.record_helper import TableHelper
from shared_code.models.bot_configuration import BotConfiguration
from shared_code.services.service_container import ServiceContainer


class BotMonitorService(ServiceContainer):
	def __init__(self):
		super().__init__()
		self.message_live_in_hours = 60 * 60 * 8
		self.all_workers: [str] = ["worker-1", "worker-2", "worker-3"]

	async def invoke_reddit_polling(self, message: func.QueueMessage) -> None:
		logging.info(f":: Starting BotMonitorService invoke_reddit_polling")
		try:
			incoming_message: BotConfiguration = self.handle_message(message)

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

	async def invoke_data_query(self, message) -> None:
		logging.info(f":: Starting BotMonitorService invoke_data_query")
		try:
			bot_config: BotConfiguration = self.handle_message(message)
			bot_name = bot_config.Name
			self.set_reddit_instance(bot_name)

			pending_submissions = self.repository.search_for_pending("Submission", bot_name, limit=100)
			logging.info(f":: Handling submissions for {bot_name}")
			for record in pending_submissions:
				await self.handle_incoming_record(record)
			logging.info(f":: Submission Handling Complete for {bot_name}")
			logging.info(f":: Fetching latest Comments For {bot_name}")
			pending_comments = self.repository.search_for_pending("Comment", bot_name, limit=100)

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
			max_probability = int(os.environ["MaxProbability"])
			reply_probability_target: int = random.randint(0, max_probability)
			if record.InputType == "Submission":
				session.commit()
				logging.info(f":: Sending {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation to {record.Subreddit} on {worker}")
				foo = self.table_to_dict(entity)
				queue.send_message(json.dumps(foo), time_to_live=self.message_live_in_hours)
				return None

			if record.ReplyProbability >= max_probability and record.InputType == "Comment":
				session.commit()
				logging.info(f":: Sending {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation to {record.Subreddit} on {worker}")
				foo = self.table_to_dict(entity)
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
			submission = await self.reddit_instance.submission(id=comment.submission.id)
		except Exception as e:
			logging.error(f":: Error Attempting To Get Submission for entity {e}")
			return None

		logging.debug(f":: Mapping Input {comment.id} for {comment.subreddit.display_name}")
		mapped_input: TableRecord = self.table_helper.map_base_to_message(
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

	@staticmethod
	def chain_listing_generators(*iterables):
		for it in iterables:
			for element in it:
				if element is None:
					break
				else:
					yield element

	@staticmethod
	def handle_message(message) -> BotConfiguration:
		try:
			message_json = message.get_body().decode('utf-8')
			incoming_message: BotConfiguration = json.loads(message_json, object_hook=lambda d: BotConfiguration(**d))
			return incoming_message
		except Exception:
			temp = TableHelper.handle_incoming_message(message)
			message_json = json.dumps(temp)
		incoming_message: BotConfiguration = json.loads(message_json, object_hook=lambda d: BotConfiguration(**d))
		return incoming_message

	@staticmethod
	def table_to_dict(tableRecord: TableRecord) -> dict:
		return {
			"Id": tableRecord.Id,
			"RedditId": tableRecord.RedditId,
			"Subreddit":  tableRecord.Subreddit,
			"InputType":  tableRecord.InputType,
			"Author":  tableRecord.Author,
			"RespondingBot":  tableRecord.RespondingBot,
			"TextGenerationPrompt":  tableRecord.TextGenerationPrompt,
			"TextGenerationResponse":  tableRecord.TextGenerationResponse,
			"HasResponded":  tableRecord.HasResponded,
			"Status":  tableRecord.Status,
			"ReplyProbability":  tableRecord.ReplyProbability,
			"Url":  tableRecord.Url
		}