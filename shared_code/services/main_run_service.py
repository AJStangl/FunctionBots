import datetime
import json
import logging
import os
import random
from typing import Optional
from datetime import datetime, timedelta
import azure.functions as func
from asyncpraw.models import Submission, Subreddit
from asyncpraw.models.comment_forest import CommentForest
from asyncpraw.reddit import Redditor, Reddit, Comment
from azure.storage.queue import TextBase64EncodePolicy

from shared_code.database.table_record import TableRecord
from shared_code.database.repository import DataRepository
from shared_code.helpers.record_helper import TableHelper
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.helpers.reply_logic import ReplyLogic
from shared_code.helpers.tagging import Tagging
from shared_code.models.bot_configuration import BotConfiguration
from shared_code.services.reply_service import ReplyService
from shared_code.storage_proxies.service_proxy import QueueServiceProxy


class BotMonitorService:
	def __init__(self):
		self.reddit_helper: RedditManager = RedditManager()
		self.repository: DataRepository = DataRepository()
		self.queue_proxy: QueueServiceProxy = QueueServiceProxy()
		self.reply_service: ReplyService = ReplyService()
		self.message_live_in_hours = 60 * 60 * 8
		self.all_workers: [str] = ["worker-1", "worker-2", "worker-3"]
		self.max_search_time = int(os.environ["MaxSearchSeconds"])
		self.reddit_instance: Optional[Reddit] = None

	async def invoke_forest_crawl(self, message: func.QueueMessage) -> None:
		try:
			forest_message = self.handle_forest_message(message)
			user_name = forest_message['user']
			comment_id = forest_message['comment_id']
			existing = self.repository.get_entity_by_id(f"{comment_id}|{user_name}")
			if existing:
				return

			instance = self.reddit_helper.get_praw_instance_for_bot(user_name)

			comment: Comment = await instance.comment(id=comment_id, fetch=True)

			probability: int = await ReplyLogic(instance).calculate_reply_probability(comment)

			submission = await self.reddit_instance.submission(id=comment.submission.id)

			try:
				user: Redditor = await instance.user.me()
			except Exception as e:
				logging.error(e)
				return

			logging.debug(f":: {comment.id} {comment.author} {user.name} {submission.subreddit}")

			logging.debug(f":: Mapping Input {comment.id} for {comment.subreddit.display_name}")
			mapped_input: TableRecord = TableHelper.map_base_to_message(
				reddit_id=comment.id,
				sub_reddit=comment.subreddit.display_name,
				input_type="Comment",
				submitted_date=submission.created,
				author=getattr(comment.author, 'name', ''),
				responding_bot=user.name,
				time_in_hours=self.timestamp_to_hours(comment.created),
				reply_probability=probability,
				url=comment.permalink)

			entity = self.repository.create_if_not_exist(mapped_input)
			if entity:
				logging.info(f":: Inserting Record comment {comment.id} with probability {probability} for {user.name}")
				return entity
		finally:
			pass

	async def invoke_reddit_polling(self, message: func.QueueMessage) -> None:
		try:
			incoming_message: BotConfiguration = self.handle_message(message)

			bot_name: str = incoming_message.Name

			if self.reddit_instance is None:
				reddit: Reddit = self.reddit_helper.get_praw_instance_for_bot(bot_name)
				self.reddit_instance = reddit

			reply_logic: ReplyLogic = ReplyLogic(self.reddit_instance)

			try:
				user: Redditor = await self.reddit_instance.user.me()
			except Exception as e:
				logging.error(f"::Error Getting User...Exiting -- {e}")
				return None

			subs: str = self.reddit_helper.get_subs_from_configuration(bot_name)

			subreddit: Subreddit = await self.reddit_instance.subreddit(subs)

			logging.info(f":: Collecting Submissions for {bot_name}")

			total_query_date = datetime.now() + timedelta(minutes=5)
			async for submission in subreddit.new(limit=30):
				if total_query_date < datetime.now():
					logging.info(f":: Max time exceeded for submission processing...{bot_name}")

				try:
					submission.comment_sort = "new"
					await submission.load()
				except Exception as e:
					logging.error(f":: Error loading Submission with {e}...Continuing")
					continue

				logging.debug(f"::{submission.subreddit} - {submission} {submission.author}")

				await self.insert_submission_to_table(submission, user, reply_logic)

				comment_forrest: CommentForest = submission.comments

				try:
					await comment_forrest.replace_more(limit=None)
				except Exception as e:
					logging.error(f":: Error getting comment forest with {e}...Continuing")
					continue

				all_comments = await comment_forrest.list()
				all_comments.sort(key=lambda x: x.created_utc)

				end_time = datetime.now() + timedelta(minutes=5)
				for comment in all_comments:
					if end_time < datetime.now():
						logging.info(f":: Max time exceeded for processing comments...{bot_name}")
						break
					try:
						await comment.load()
					except Exception as e:
						logging.error(f":: Error loading comment with {e}...Continuing")
						continue

					logging.debug(f"::{submission.subreddit} - {submission} {submission.author} {comment} {comment.author}")
					await self.insert_comment_to_table(comment, user, reply_logic)

			logging.info(f":: Polling Method Complete For {bot_name}")
			return None
		finally:
			await self.reddit_instance.close()

	async def invoke_data_query(self, message):
		try:
			bot_config: BotConfiguration = self.handle_message(message)
			bot_name = bot_config.Name

			if self.reddit_instance is None:
				reddit: Reddit = self.reddit_helper.get_praw_instance_for_bot(bot_name)
				self.reddit_instance = reddit

			tagging: Tagging = Tagging(self.reddit_instance)

			logging.info(f":: Handling pending comments and submissions from database for {bot_name}")

			unsent_reply_count = 0
			unsent_replies = self.repository.search_for_unsent_replies(bot_name)
			for reply in unsent_replies:
				if reply is None:
					logging.info(f":: No records found for comments or submission to process for {bot_name}")
					continue
				unsent_reply_count += 1
				message_string = json.dumps(reply.as_dict())
				reply_client = self.queue_proxy.service.get_queue_client("reply-queue", message_encode_policy=TextBase64EncodePolicy())
				logging.info(f":: Sending Message To Unsent Message Reply Queue for {bot_name}")
				reply_client.send_message(message_string)
				reply_client.close()

			logging.info(f":: Checked for unsent reply events - {bot_name}. Found {unsent_reply_count}")

			logging.info(f":: Fetching latest Submissions For {bot_name}")
			pending_submissions = self.repository.search_for_pending("Submission", bot_name, limit=30)
			logging.info(f":: Handling submissions for {bot_name}")
			for record in pending_submissions:
				await self.handle_incoming_record(record, tagging)
			logging.info(f":: Submission Handling Complete for {bot_name}")

			logging.info(f":: Fetching latest Comments For {bot_name}")
			pending_comments = self.repository.search_for_pending("Comment", bot_name, limit=30)

			end_time = datetime.now() + timedelta(minutes=3)
			logging.info(f":: Handling comments for {bot_name} - Attempting for {end_time}...")
			for record in pending_comments:
				if end_time < datetime.now():
					logging.info(":: Max time exceeded for processing comments...")
					break
				await self.handle_incoming_record(record, tagging)
			logging.info(f":: Submission comments Complete for {bot_name}")

			return None

		finally:
			if self.reddit_instance:
				await self.reddit_instance.close()

	async def handle_incoming_record(self, record, tagging):
		worker: str = random.choice(self.all_workers)
		queue = self.queue_proxy.service.get_queue_client(worker, message_encode_policy=TextBase64EncodePolicy())
		try:
			record = record['TableRecord']
			record.Status = 1
			logging.debug(f":: starting input processing on {record}")
			processed = await self.process_input(record, tagging)
			logging.debug(f":: completed input processing on {record}")

			record.TextGenerationPrompt = processed
			reply_probability_target: int = random.randint(0, int(os.environ["MaxProbability"]))
			if record.InputType == "Submission":
				logging.info(f":: Sending {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation to {record.Subreddit} on {worker}")
				queue.send_message(json.dumps(record.as_dict()), time_to_live=self.message_live_in_hours)
				self.repository.update_entity(record)
				return None

			if record.ReplyProbability > reply_probability_target and record.InputType == "Comment":
				logging.info(f":: Sending {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation to {record.Subreddit} on {worker}")
				queue.send_message(json.dumps(record.as_dict()), time_to_live=self.message_live_in_hours)
				self.repository.update_entity(record)
				return None

			else:
				logging.debug(f":: Ignoring {record.InputType} for {record.RespondingBot} has a Probability of {record.ReplyProbability} but needs {reply_probability_target}")
				record.Status = 2
				self.repository.update_entity(record)
				return None
		finally:
			queue.close()

	async def process_input(self, record: TableRecord, tagging: Tagging) -> Optional[str]:
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
				history: str = await tagging.collate_tagged_comment_history(thing_submission)
			except Exception as e:
				logging.error(f": error Attemping to get history. Returning None {e}")
				return None

			cleaned_history: str = tagging.remove_username_mentions_from_string(history, record.RespondingBot)

			try:
				reply_start_tag: str = await tagging.get_reply_tag(thing_submission)
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

			history: str = await tagging.collate_tagged_comment_history(thing_comment)
			cleaned_history: str = tagging.remove_username_mentions_from_string(history, record.RespondingBot)
			reply_start_tag: str = await tagging.get_reply_tag(thing_comment)
			prompt: str = cleaned_history + reply_start_tag
			return prompt

	async def insert_submission_to_table(self, submission: Submission, user: Redditor, reply_probability: ReplyLogic) -> Optional[TableRecord]:
		existing = self.repository.get_entity_by_id(f"{submission.id}|{user.name}")
		if existing:
			return existing

		probability: int = await reply_probability.calculate_reply_probability(submission)
		if user.name == getattr(submission.author, 'name', ''):
			probability = 0

		mapped_input: TableRecord = TableHelper.map_base_to_message(
			reddit_id=submission.id,
			sub_reddit=submission.subreddit.display_name,
			input_type="Submission",
			time_in_hours=self.timestamp_to_hours(submission.created),
			submitted_date=submission.created,
			author=getattr(submission.author, 'name', ''),
			responding_bot=user.name,
			reply_probability=probability,
			url=submission.url
		)

		entity = self.repository.create_if_not_exist(mapped_input)
		if entity:
			logging.info(f":: Inserting Record submission {submission.id} with probability {probability} for {user.name}")
			return entity

	async def insert_comment_to_table(self, comment: Comment, user: Redditor, reply_probability: ReplyLogic) -> Optional[TableRecord]:
		existing = self.repository.get_entity_by_id(f"{comment.id}|{user.name}")
		if existing:
			return existing
		try:
			probability: int = await reply_probability.calculate_reply_probability(comment)
		except Exception as e:
			logging.error(f":: Error Attempting Probability Calculation {e}")
			return None
		try:
			submission = await self.reddit_instance.submission(id=comment.submission.id)
		except Exception as e:
			logging.error(f":: Error Attempting To Get Submission for entity {e}")
			return None


		logging.debug(f":: {comment.id} {comment.author} {user.name} {submission.subreddit}")
		logging.debug(f":: Mapping Input {comment.id} for {comment.subreddit.display_name}")
		mapped_input: TableRecord = TableHelper.map_base_to_message(
			reddit_id=comment.id,
			sub_reddit=comment.subreddit.display_name,
			input_type="Comment",
			submitted_date=submission.created,
			author=getattr(comment.author, 'name', ''),
			responding_bot=user.name,
			time_in_hours=self.timestamp_to_hours(comment.created),
			reply_probability=probability,
			url=comment.permalink)

		entity = self.repository.create_if_not_exist(mapped_input)
		if entity:
			logging.info(f":: Inserting Record comment {comment.id} with probability {probability} for {user.name}")
			return entity

	@staticmethod
	def timestamp_to_hours(utc_timestamp) -> int:
		return int(
			(datetime.utcnow() - datetime.fromtimestamp(utc_timestamp)).total_seconds() / 3600) - 4

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
	def handle_forest_message(message) -> dict:
		message_json = message.get_body().decode('utf-8')
		incoming_message = json.loads(message_json)
		return incoming_message

