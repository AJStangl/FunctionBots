import datetime
import logging

from azure.core.paging import ItemPaged
from azure.storage.queue import QueueServiceClient, QueueClient, QueueMessage
from praw import Reddit
from praw.models import Submission, Comment

from shared_code.database.instance import TableRecord
from shared_code.helpers.record_helper import TableHelper
from shared_code.database.repository import DataRepository
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.helpers.tagging import TaggingMixin
from shared_code.storage_proxies.service_proxy import QueueServiceProxy


class ReplyService:
	def __init__(self, instance: Reddit):
		self.logging = logging.getLogger(__name__)
		self.bad_key_words = ["removed", "nouniqueideas007"]
		self.tagging: TaggingMixin = TaggingMixin()
		self.reddit_manager: RedditManager = RedditManager()
		self.queue_service: QueueServiceClient = QueueServiceProxy().service
		self.repository: DataRepository = DataRepository()
		self.queue_client: QueueClient = self.queue_service.get_queue_client("reply-queue")
		self.reddit_instance: Reddit = instance

	def invoke(self) -> None:
		self.logging.info(f":: Initializing Reply Processing")
		if len(self.queue_client.peek_messages()) == 0:
			self.logging.info(f":: No New Messages for queue")
			return None

		try:
			messages: ItemPaged[QueueMessage] = self.queue_client.receive_messages()
		except Exception as e:
			self.logging.info(f":: Exception Occurred While Handling Retrieval Of Messages. {e}")
			return None

		self.handle_messages(messages)
		logging.info(f":: Reply Process Complete")

		return None

	def handle_messages(self, messages):
		for message in messages:
			self.logging.info(f":: Handling Messages From Iterator")

			self.queue_client.delete_message(message)

			record: TableRecord = TableHelper.handle_incoming_message(message)

			prompt: str = record["TextGenerationPrompt"]

			response: str = record["TextGenerationResponse"]

			extract: dict = self.tagging.extract_reply_from_generated_text(prompt, response)

			reddit: Reddit = self.reddit_instance

			entity: TableRecord = self.repository.get_entity_by_id(record["Id"])

			if not extract['body']:
				logging.info(f":: No Body Present for {record.PartitionKey}")

			for item in self.bad_key_words:
				if extract['body'] in item:
					logging.info(f"Response has negative keyword - {item}")
					entity.HasResponded = True
					entity.Status = 3
					entity.DateTimeSubmitted = datetime.datetime.now()
					self.repository.update_entity(entity)

			if entity.InputType == "Submission":
				sub_instance: Submission = reddit.submission(id=entity.RedditId)
				logging.info(f":: Sending Out Reply To Submission - {entity.RedditId}")
				sub_instance.reply(extract['body'])
				entity.HasResponded = True
				entity.Status = 4
				entity.DateTimeSubmitted = datetime.datetime.now()
				entity.TextGenerationResponse = extract['body']
				self.repository.update_entity(entity)

			if entity.InputType == "Comment":
				logging.info(f":: Sending Out Reply To Comment - {entity.RedditId}")
				comment_instance: Comment = reddit.comment(id=entity.RedditId)
				comment_instance.reply(extract['body'])
				entity.HasResponded = True
				entity.Status = 4
				entity.DateTimeSubmitted = datetime.datetime.now()
				entity.TextGenerationResponse = extract['body']
				self.repository.update_entity(entity)
