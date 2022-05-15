from azure.core.credentials import AzureNamedKeyCredential
from azure.data.tables import TableServiceClient, TableClient
import logging

class TableServiceProxy(object):

	logger = logging.getLogger('azure.core.pipeline.policies.http_logging_policy')
	logger.setLevel(logging.WARNING)

	def __init__(self):
		# Note: These values are specific to running the azure storage emulator locally.
		self.account_name = "devstoreaccount1"
		self.account_key = "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="
		self.credential = AzureNamedKeyCredential(self.account_name, self.account_key)
		self.service = TableServiceClient(
			credential=self.credential,
			endpoint="http://127.0.0.1:10002/devstoreaccount1"
		)

	def get_client(self) -> TableClient:
		return self.service.get_table_client("tracking")


