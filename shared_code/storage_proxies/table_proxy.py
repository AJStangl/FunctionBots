import json

from azure.core.credentials import AzureNamedKeyCredential
from azure.data.tables import TableServiceClient, TableClient
import logging

from shared_code.models.table_data import TableRecord


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
		return self.service.create_table_if_not_exists("tracking")

	def entity_exists(self, entity: TableRecord) -> bool:
		client = self.get_client()
		raw = entity.json
		try:
			result = client.get_entity(partition_key=entity.PartitionKey, row_key=entity.RowKey)
			if result:
				return True
		except Exception:
			client.create_entity(entity=json.loads(raw))
			return False



