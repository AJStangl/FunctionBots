import datetime
import json
import logging
import os
import random
from typing import Optional

import azure.functions as func
from asyncpraw.models import Submission, Subreddit
from asyncpraw.models.comment_forest import CommentForest
from asyncpraw.reddit import Redditor, Reddit, Comment
from azure.storage.queue import TextBase64EncodePolicy

from shared_code.database.instance import TableRecord
from shared_code.database.repository import DataRepository
from shared_code.helpers.record_helper import TableHelper
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.helpers.reply_logic import ReplyLogic
from shared_code.helpers.tagging import TaggingMixin
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

	async def invoke(self, message: func.QueueMessage):
		try:
			incoming_message: BotConfiguration = self.handle_message(message)

			bot_name: str = incoming_message.Name

			if self.reddit_instance is None:
				reddit: Reddit = self.reddit_helper.get_praw_instance_for_bot(bot_name)
				self.reddit_instance = reddit

			reply_logic: ReplyLogic = ReplyLogic(self.reddit_instance)

			user: Redditor = await self.reddit_instance.user.me()

			subs: str = self.reddit_helper.get_subs_from_configuration(bot_name)

			subreddit: Subreddit = await self.reddit_instance.subreddit(subs)

			logging.info(f":: Collecting Submissions for {bot_name}")

			async for submission in subreddit.new(limit=15):
				await submission.load()

				logging.info(f"::{submission.subreddit} - {submission} {submission.author}")
				await self.insert_submission_to_table(submission, user, reply_logic)

				comment_forrest: CommentForest = submission.comments
				await comment_forrest.replace_more(limit=None)

				async for comment in comment_forrest:
					await comment.load()

					logging.info(
						f"::{submission.subreddit} - {submission} {submission.author} {comment} {comment.author}")
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
			tagging: TaggingMixin = TaggingMixin(self.reddit_instance)

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

			logging.info(f":: Fetching latest Comments For {bot_name}")
			pending_comments = self.repository.search_for_pending("Comment", bot_name, limit=30)

			logging.info(f":: Fetching latest Submissions For {bot_name}")
			pending_submissions = self.repository.search_for_pending("Submission", bot_name, limit=30)

			for record in self.chain_listing_generators(pending_comments, pending_submissions):
				queue = self.queue_proxy.service.get_queue_client(random.choice(self.all_workers), message_encode_policy=TextBase64EncodePolicy())
				if record is None:
					logging.info(f":: No records found for comments or submission to process for {bot_name}")
					continue

				# Extract the record and set the status
				record = record['TableRecord']
				record.Status = 1
				processed = await self.process_input(record, tagging)
				if processed is None:
					logging.info(f":: Failed To Process {record.RedditId} for {record.RespondingBot}")
					continue

				record.TextGenerationPrompt = processed
				reply_probability_target: int = random.randint(0, 100)
				if record.InputType == "Submission":
					logging.info(f":: Sending {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation to {record.Subreddit}")
					queue.send_message(json.dumps(record.as_dict()), time_to_live=self.message_live_in_hours)
					self.repository.update_entity(record)
					queue.close()
					continue

				if record.ReplyProbability > reply_probability_target and record.InputType == "Comment":
					logging.info(f":: Sending {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation to {record.Subreddit}")
					queue.send_message(json.dumps(record.as_dict()), time_to_live=self.message_live_in_hours)
					self.repository.update_entity(record)
					queue.close()
					continue

				else:
					logging.info(f":: Ignoring {record.InputType} for {record.RespondingBot} has a Probability of {record.ReplyProbability} but needs {reply_probability_target}")
					record.Status = 2
					self.repository.update_entity(record)
					queue.close()
					continue

		finally:
			if self.reddit_instance:
				await self.reddit_instance.close()

	async def process_input(self, record: TableRecord, tagging: TaggingMixin) -> Optional[str]:
		if record.InputType == "Submission":
			thing_submission: Submission = await self.reddit_instance.submission(id=record.RedditId, fetch=True)
			if thing_submission is None:
				return None

			await thing_submission.load()

			history: str = await tagging.collate_tagged_comment_history(thing_submission)

			cleaned_history: str = tagging.remove_username_mentions_from_string(history, record.RespondingBot)
			reply_start_tag: str = await tagging.get_reply_tag(thing_submission)
			prompt: str = cleaned_history + reply_start_tag
			return prompt

		if record.InputType == "Comment":
			thing_comment: Comment = await self.reddit_instance.comment(id=record.RedditId, fetch=True)
			if thing_comment is None:
				return None

			await thing_comment.load()

			history: str = await tagging.collate_tagged_comment_history(thing_comment)
			cleaned_history: str = tagging.remove_username_mentions_from_string(history, record.RespondingBot)
			reply_start_tag: str = await tagging.get_reply_tag(thing_comment)
			prompt: str = cleaned_history + reply_start_tag
			return prompt

	async def insert_submission_to_table(self, submission: Submission, user: Redditor, reply_probability: ReplyLogic) -> Optional[TableRecord]:
		# Ignore when submission is the same for the submitter and responder
		if user.name == getattr(submission.author, 'name', ''):
			return None

		existing = self.repository.get_entity_by_id(f"{submission.id}|{user.name}")
		if existing:
			return existing

		probability: int = await reply_probability.calculate_reply_probability(submission)

		if probability == 0:
			logging.debug(f":: Reply Probability for {submission.id} is {probability} for bot - {user.name}")
			return None

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
			logging.info(
				f":: Inserting Record submission {submission.id} with probability {probability} for {user.name}")
			return entity

	async def insert_comment_to_table(self, comment: Comment, user: Redditor, reply_probability: ReplyLogic) -> Optional[TableRecord]:
		existing = self.repository.get_entity_by_id(f"{comment.id}|{user.name}")
		if existing:
			return existing
		probability: int = await reply_probability.calculate_reply_probability(comment)
		submission = await self.reddit_instance.submission(id=comment.submission.id)
		logging.debug(f":: {comment.id} {comment.author} {user.name} {submission.subreddit}")

		if probability == 0:
			logging.info(f":: Reply Probability for {comment.id} is {probability} for bot - {user.name}")
			return None

		logging.info(f":: Mapping Input {comment.id} for {comment.subreddit.display_name}")
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
			(datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(utc_timestamp)).total_seconds() / 3600) - 4

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
