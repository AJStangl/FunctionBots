import json
import logging
import random
from datetime import datetime
from enum import Enum
from typing import Optional

import azure.functions as func
from azure.core.paging import ItemPaged
from azure.data.tables import TableClient, TableEntity
from praw.models import Submission

from shared_code.helpers.reddit_helper import RedditManager
from shared_code.helpers.tagging import TaggingMixin
from shared_code.models.bot_configuration import BotConfigurationManager
from shared_code.storage_proxies.service_proxy import QueueServiceProxy
from shared_code.storage_proxies.table_proxy import TableServiceProxy, TableRecord


class WorkerType(Enum):
	COMMENT_WORKER = 0
	SUBMISSION_WORKER = 1
	PRIORITY_WORKER = 2


class ReplyPreparation:
	def __init__(self):
		self.submission_workers: [str] = ["worker-1"]
		self.comment_workers: [str] = ["worker-2", "worker-3"]
		self.bot_configuration_manager = BotConfigurationManager()
		self.table_proxy_service: TableServiceProxy = TableServiceProxy()
		self.queue_proxy_service: QueueServiceProxy = QueueServiceProxy()
		self.reddit_manager: RedditManager = RedditManager()
		self.tagging_mixin = TaggingMixin()
		self.logger = logging.getLogger(__name__)

	def invoke(self, selected_bot) -> None:
		client: TableClient = self.table_proxy_service.get_client()

		self.handle_submissions(client, selected_bot)

		self.handle_comment_results(client, selected_bot)

	def handle_submissions(self, client, selected_bot):
		self.logger.info(f":: Handling Submissions for {selected_bot}")
		query_string = f"has_responded eq false and input_type eq 'Submission' and text_generation_prompt eq '' and status eq 0 and responding_bot eq '{selected_bot}'"
		pending_submissions: ItemPaged[TableEntity] = client.query_entities(query_string)
		submission_results = []
		for page in pending_submissions:
			record: TableRecord = json.loads(json.dumps(page), object_hook=lambda d: TableRecord(**d))
			e = client.get_entity(partition_key=record.PartitionKey, row_key=record.RowKey)
			e["status"] = 1
			client.update_entity(entity=e)
			submission_results.append(record)
			break
		for record in submission_results:
			processed = self.process_input(record)
			record.text_generation_prompt = processed
			e = client.get_entity(partition_key=record.PartitionKey, row_key=record.RowKey)
			e["text_generation_prompt"] = record.text_generation_prompt
			client.update_entity(e)

			queue = self.queue_proxy_service.service.get_queue_client(self.get_random_worker(worker_type=WorkerType.SUBMISSION_WORKER))
			queue.send_message(record.json)

	def handle_comment_results(self, client, selected_bot):
		self.logger.info(f":: Handling Comments for {selected_bot}")

		comment_results = []

		query_string = f"has_responded eq false and input_type eq 'Comment' and text_generation_prompt eq '' and status eq 0 and responding_bot eq '{selected_bot}'"

		pending_comments: ItemPaged[TableEntity] = client.query_entities(query_string)

		for page in pending_comments:
			record: TableRecord = json.loads(json.dumps(page), object_hook=lambda d: TableRecord(**d))
			comment_results.append(record)
			e = client.get_entity(partition_key=record.PartitionKey, row_key=record.RowKey)
			e["status"] = 1
			client.update_entity(entity=e)

			break

		for record in comment_results:
			processed = self.process_input(record)
			record.text_generation_prompt = processed

			e = client.get_entity(partition_key=record.PartitionKey, row_key=record.RowKey)
			e["text_generation_prompt"] = record.text_generation_prompt
			client.update_entity(entity=e)

			# Check if the bot author is not a one our the bots running send to priority queue
			if self.bot_configuration_manager.get_configuration_by_name(record.author) is None:
				logging.info(":: Non Bot - Sending to Priority Queue")
				queue = self.queue_proxy_service.service.get_queue_client(self.get_random_worker(WorkerType.PRIORITY_WORKER))
				e = client.get_entity(partition_key=record.PartitionKey, row_key=record.RowKey)
				e["status"] = 1
				client.update_entity(e)

				queue.send_message(record.json, time_to_live=(60 * 60 * 12))

			should_reply = self.get_random_probability()

			if should_reply:
				queue = self.queue_proxy_service.service.get_queue_client(self.get_random_worker(WorkerType.COMMENT_WORKER))
				e = client.get_entity(partition_key=record.PartitionKey, row_key=record.RowKey)
				e["status"] = 1
				client.update_entity(e)
				# let message live for 12 hours
				queue.send_message(record.json, time_to_live=(60 * 60 * 12))

			else:
				# We ignore it and set the status to ignored
				e = client.get_entity(partition_key=record.PartitionKey, row_key=record.RowKey)
				e["status"] = 2
				client.update_entity(e)

	def process_input(self, incoming_message: TableRecord) -> Optional[str]:

		instance = self.reddit_manager.get_praw_instance_for_bot(incoming_message.responding_bot)

		if incoming_message.input_type == "Submission":
			thing: Submission = instance.submission(id=incoming_message.id)
			history = self.tagging_mixin.collate_tagged_comment_history(thing)
			cleaned_history = self.tagging_mixin.remove_username_mentions_from_string(history, incoming_message.responding_bot)
			reply_start_tag = self.tagging_mixin.get_reply_tag(thing, incoming_message.responding_bot)
			prompt = cleaned_history + reply_start_tag
			return prompt

		if incoming_message.input_type == "Comment":
			thing = instance.comment(id=incoming_message.id)
			history = self.tagging_mixin.collate_tagged_comment_history(thing)
			cleaned_history = self.tagging_mixin.remove_username_mentions_from_string(history, incoming_message.responding_bot)
			reply_start_tag = self.tagging_mixin.get_reply_tag(thing, incoming_message.responding_bot)
			prompt = cleaned_history + reply_start_tag
			return prompt

	@staticmethod
	def timestamp_to_hours(utc_timestamp) -> float:
		return (datetime.utcnow() - datetime.fromtimestamp(utc_timestamp)).total_seconds() / 3600

	@staticmethod
	def get_random_probability() -> bool:
		choice = random.choice(list(range(1, 10)))
		return choice % 3 == 0

	def get_random_worker(self, worker_type: WorkerType) -> str:
		if worker_type == worker_type.SUBMISSION_WORKER or worker_type == worker_type.PRIORITY_WORKER:
			return random.choice(self.submission_workers)
		return random.choice(self.comment_workers)





