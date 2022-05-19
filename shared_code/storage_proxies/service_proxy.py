from azure.storage.queue import QueueService
import azure.storage.queue.models


class QueueServiceProxy(object):
	def __init__(self):
		# Note: These values are specific to running the azure storage emulator locally.
		self.account_name = "devstoreaccount1"
		self.account_key = "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="
		self.connection_string = "AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;DefaultEndpointsProtocol=http;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
		self.is_emulated = True
		self.service = QueueService(account_name=self.account_name, account_key=self.account_key,
									connection_string=self.connection_string, is_emulated=self.is_emulated)

	def put_message(self, queue_name: str, content) -> azure.storage.queue.models.QueueMessage:
		return self.service.put_message(queue_name, content=content)

	def ensure_created(self):
		self.service.create_queue("content-queue")
		self.service.create_queue("prompt-queue")
		self.service.create_queue("reply-queue")
