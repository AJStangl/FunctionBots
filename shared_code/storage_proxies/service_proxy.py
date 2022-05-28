from azure.storage.queue import QueueMessage, QueueServiceClient
import azure.storage.queue

from shared_code.models.azure_configuration import FunctionAppConfiguration


class QueueServiceProxy(object):
	def __init__(self):
		config = FunctionAppConfiguration()
		self.account_name = config.account_name
		self.account_key = config.account_key
		self.connection_string = config.connection_string
		self.is_emulated = config.is_emulated
		self.service = QueueServiceClient.from_connection_string(self.connection_string, config.get_credentials())

	def put_message(self, queue_name: str, content) -> azure.storage.queue.QueueMessage:
		return self.service.put_message(queue_name, content=content)

	def ensure_created(self) -> None:
		self.service.create_queue("content-queue")
		self.service.create_queue("prompt-queue")
		self.service.create_queue("reply-queue")
		return
