import logging

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
		self.service: QueueServiceClient = QueueServiceClient.from_connection_string(self.connection_string)

	def put_message(self, queue_name: str, content) -> azure.storage.queue.QueueMessage:
		return self.service.put_message(queue_name, content=content)

	def ensure_created(self) -> None:
		self.try_create_queue("content-queue")
		self.try_create_queue("poll-queue")
		self.try_create_queue("prompt-queue")
		self.try_create_queue("reply-queue")
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
		self.try_delete_queue("content-queue")
		self.try_delete_queue("poll-queue")
		self.try_delete_queue("prompt-queue")
		self.try_delete_queue("reply-queue")
		self.try_delete_queue("reply-queue")

		return None

	def clear_queue(self, queue_name) -> None:
		logging.info(f":: Deleting Queue {queue_name}")

		if queue_name == "*":
			self.delete_all()
			self.ensure_created()
			return

		self.service.delete_queue(queue_name)

		logging.info(f":: Creating Queue {queue_name}")

		self.service.create_queue(queue_name)
		return

	def create_service_client(self, queue_name) -> QueueClient:
		return QueueClient.from_connection_string(self.connection_string, queue_name)
