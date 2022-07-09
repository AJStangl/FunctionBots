import datetime
import json
import logging
import os
import random
import time
from typing import Optional
import azure.functions as func
from asyncpraw.models import Submission, Subreddit
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


cached_instance = None

class BotMonitorService:
	def __init__(self):
		self.reddit_helper: RedditManager = RedditManager()
		self.repository: DataRepository = DataRepository()
		self.queue_proxy: QueueServiceProxy = QueueServiceProxy()
		self.reply_service: ReplyService = ReplyService()
		self.message_live_in_hours = 60 * 60 * 8
		self.all_workers: [str] = ["worker-1", "worker-2", "worker-3"]
		self.max_search_time = int(os.environ["MaxSearchSeconds"])
		self.reddit_instance: Optional[Reddit] = cached_instance

	async def invoke(self, message: func.QueueMessage):

		# Decode incoming message
		################################################################################################################
		try:
			message_json = message.get_body().decode('utf-8')
		except Exception:
			temp = TableHelper.handle_incoming_message(message)
			message_json = json.dumps(temp)
		incoming_message: BotConfiguration = json.loads(message_json, object_hook=lambda d: BotConfiguration(**d))
		bot_name: str = incoming_message.Name
		################################################################################################################

		# Wire-Up dependencies
		################################################################################################################
		if self.reddit_instance is None:
			reddit: Reddit = self.reddit_helper.get_praw_instance_for_bot(bot_name)
			self.reddit_instance = reddit

		tagging: TaggingMixin = TaggingMixin(self.reddit_instance)
		reply_logic: ReplyLogic = ReplyLogic(self.reddit_instance)
		################################################################################################################

		user: Redditor = await self.reddit_instance.user.me()
		subs: str = self.reddit_helper.get_subs_from_configuration(bot_name)

		subreddit: Subreddit = await self.reddit_instance.subreddit(subs)

		logging.info(f":: Initializing Reply Before Main Routine for {bot_name}")

		# Check for messages that for whatever reason need to be replied to
		unsent_replies = self.repository.search_for_unsent_replies(bot_name)
		logging.info(f":: Check for unsent respond events for {bot_name}")
		for reply in unsent_replies:
			if reply is None:
				logging.info(f":: No records found for comments or submission to process for {bot_name}")
				continue
			message_string = json.dumps(reply.as_dict())
			reply_client = self.queue_proxy.service.get_queue_client("reply-queue", message_encode_policy=TextBase64EncodePolicy())
			reply_client.send_message(message_string)

		logging.info(f":: Initializing Reply Service for {bot_name}")
		await self.reply_service.invoke()


		# Initial Database Query For Responding
		################################################################################################################
		logging.info(f":: Handling pending comments and submissions from database for {bot_name}")

		logging.info(f":: Fetching latest Comments For {bot_name}")
		pending_comments = self.repository.search_for_pending("Comment", bot_name, 22)

		logging.info(f":: Fetching latest Submissions For {bot_name}")
		pending_submissions = self.repository.search_for_pending("Submission", bot_name, 10)

		for record in self.chain_listing_generators(pending_comments, pending_submissions):
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
			reply_probability_target: int = random.randint(0, 50)
			if record.InputType == "Submission":
				self.repository.update_entity(record)
				queue = self.queue_proxy.service.get_queue_client(random.choice(self.all_workers), message_encode_policy=TextBase64EncodePolicy())
				queue.send_message(json.dumps(record.as_dict()), time_to_live=self.message_live_in_hours)
				logging.info(f":: Sending {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation")
				continue

			if record.ReplyProbability > reply_probability_target and record.InputType == "Comment":
				queue = self.queue_proxy.service.get_queue_client(random.choice(self.all_workers), message_encode_policy=TextBase64EncodePolicy())
				queue.send_message(json.dumps(record.as_dict()), time_to_live=self.message_live_in_hours)
				self.repository.update_entity(record)
				logging.info(f":: Sending {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation")
				continue

			else:
				logging.info(f":: Ignoring {record.InputType} for {record.RespondingBot} has a Probability of {record.ReplyProbability} but needs {reply_probability_target}")
				record.Status = 2
				self.repository.update_entity(record)
				continue

		# Perform The Comment And Submission Mechanism
		####################################################################################################################
		logging.info(f":: Collecting Submissions for {bot_name}")
		start_time: float = time.time()
		async for submission in subreddit.new(limit=10):
			if submission is None:
				break
			if round(time.time() - start_time) > self.max_search_time:
				logging.info(f":: Halting Collection Past {self.max_search_time} seconds For Submissions")
				break
			await self.insert_submission_to_table(submission, user, reply_logic)

		start_time = time.time()
		logging.info(f":: Collecting Comments for {bot_name}")
		async for comment in subreddit.stream.comments(pause_after=0):
			if comment is None:
				break

			if round(time.time() - start_time) > self.max_search_time:
				logging.info(f":: Halting Collection Past {self.max_search_time} seconds For Comments")
				break

			await self.insert_comment_to_table(comment, user, reply_logic)
		####################################################################################################################

		logging.info(f":: Initializing Reply After Main Routine for {bot_name}")
		await self.reply_service.invoke()

		logging.info(f":: Polling Method Complete For {bot_name}")
		await self.reddit_instance.close()
		return None

	async def process_input(self, record: TableRecord, tagging_mixin: TaggingMixin) -> Optional[str]:
		if record.InputType == "Submission":
			thing: Submission = await self.reddit_instance.submission(id=record.RedditId)
			if thing is None:
				return None

			history: str = await tagging_mixin.collate_tagged_comment_history(thing)
			cleaned_history: str = tagging_mixin.remove_username_mentions_from_string(history, record.RespondingBot)
			reply_start_tag: str = await tagging_mixin.get_reply_tag(thing, record.RespondingBot)
			prompt: str = cleaned_history + reply_start_tag
			return prompt

		if record.InputType == "Comment":
			thing: Comment = await self.reddit_instance.comment(id=record.RedditId)
			if thing is None:
				return None

			history: str = await tagging_mixin.collate_tagged_comment_history(thing)
			cleaned_history: str = tagging_mixin.remove_username_mentions_from_string(history, record.RespondingBot)
			reply_start_tag: str = await tagging_mixin.get_reply_tag(thing, record.RespondingBot)
			prompt: str = cleaned_history + reply_start_tag
			return prompt

	async def insert_submission_to_table(self, submission: Submission, user: Redditor, reply_probability: ReplyLogic) -> Optional[TableRecord]:
		# Ignore when submission is the same for the submitter and responder
		if user.name == getattr(submission.author, 'name', ''):
			return None

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

		logging.info(f":: Inserting Record submission {submission.id} with probability {probability} for {user.name}")
		entity = self.repository.create_if_not_exist(mapped_input)
		return entity

	async def insert_comment_to_table(self, comment: Comment, user: Redditor, reply_probability: ReplyLogic) -> Optional[TableRecord]:
		probability = await reply_probability.calculate_reply_probability(comment)
		submission = await self.reddit_instance.submission(id=comment.submission.id)
		if probability == 0:
			logging.debug(f":: Reply Probability for {comment.id} is {probability} for bot - {user.name}")
			return None

		mapped_input: TableRecord = TableHelper.map_base_to_message(
			reddit_id=comment.id,
			sub_reddit=comment.subreddit.display_name,
			input_type="Comment",
			submitted_date=submission.created,
			author=getattr(comment.author, 'name', ''),
			responding_bot=user.name,
			time_in_hours= self.timestamp_to_hours(comment.created),
			reply_probability=probability,
			url=comment.permalink)

		logging.info(f":: Inserting Record comment {comment.id} with probability {probability} for {user.name}")
		entity = self.repository.create_if_not_exist(mapped_input)

		return entity

	@staticmethod
	def timestamp_to_hours(utc_timestamp) -> int:
		return int((datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(utc_timestamp)).total_seconds() / 3600) - 4

	@staticmethod
	def chain_listing_generators(*iterables):
		for it in iterables:
			for element in it:
				if element is None:
					break
				else:
					yield element


