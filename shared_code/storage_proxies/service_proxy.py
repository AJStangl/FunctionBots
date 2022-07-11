import logging

from azure.core.paging import ItemPaged
from azure.storage.queue import QueueMessage, QueueServiceClient, TextBase64EncodePolicy, TextBase64DecodePolicy, \
	QueueClient
import azure.storage.queue

from shared_code.models.azure_configuration import FunctionAppConfiguration


class QueueServiceProxy(object):
	logger = logging.getLogger("azure.core.pipeline.policies.http_logging_policy")
	logger.setLevel(logging.WARNING)

	def __init__(self):
		self.config: FunctionAppConfiguration = FunctionAppConfiguration()
		self.account_name: str = self.config.account_name
		self.account_key: str = self.config.account_key
		self.connection_string: str = self.config.connection_string
		self.is_emulated: bool = self.config.is_emulated
		self.service: QueueServiceClient = QueueServiceClient.from_connection_string(self.connection_string, encode_policy=TextBase64EncodePolicy())
		self.queues: dict = {
			"poll": "poll-queue",
			"reply": "reply-queue",
			"data": "data-queue",
			"worker1": "worker-1",
			"worker2": "worker-2",
			"worker3": "worker-3",
			"submission": "submission-worker",
		}

	def put_message(self, queue_name: str, content) -> azure.storage.queue.QueueMessage:
		return self.service.put_message(queue_name, content=content)

	def ensure_created(self) -> None:
		for queue in self.queues.keys():
			self.try_create_queue(self.queues[queue])
		return None

	def try_delete_queue(self, name) -> None:
		try:
			self.service.delete_queue(name)
			return None
		except Exception:
			return None

	def try_create_queue(self, name) -> None:
		try:
			self.service.create_queue(name)
			return None
		except Exception:
			return None

	def delete_all(self) -> None:
		for queue in self.queues.keys():
			self.try_delete_queue(self.queues[queue])
		return None

	def clear_queue(self, queue_name) -> None:
		logging.info(f":: Deleting Queue {queue_name}")
		queue_client: QueueClient = self.service.get_queue_client(queue_name)
		response: ItemPaged[QueueMessage] = queue_client.receive_messages(messages_per_page=32)
		page_count = 1
		for message_batch in response.by_page():
			logging.info(f":: Clearing Page {page_count} for {queue_name}")
			for message in message_batch:
				queue_client.delete_message(message)
				page_count += 1
		logging.info(f":: Cleared {queue_name}")

		return None

	def get_total_message_count(self, queue_name) -> dict:
		queue_client: QueueClient = self.service.get_queue_client(queue_name)
		response: ItemPaged[QueueMessage] = queue_client.receive_messages(messages_per_page=32)
		page_count = 1
		total_messages = 0

		for message_batch in response.by_page():
			for message in message_batch:
				total_messages += 1
			page_count += 1
		return {
			"page_count": page_count,
			"total_messages": total_messages
		}

	def create_service_client(self, queue_name) -> QueueClient:
		return QueueClient.from_connection_string(self.connection_string, queue_name)
