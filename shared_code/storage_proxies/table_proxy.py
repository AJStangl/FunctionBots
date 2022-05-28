import json

from azure.core.credentials import AzureNamedKeyCredential
from azure.data.tables import TableServiceClient, TableClient
import logging

from shared_code.models.table_data import TableRecord
from shared_code.models.azure_configuration import FunctionAppConfiguration


class TableServiceProxy(object):

	logger = logging.getLogger('azure.core.pipeline.policies.http_logging_policy')
	logger.setLevel(logging.WARNING)

	def __init__(self):
		config = FunctionAppConfiguration()
		self.account_name = config.account_name
		self.account_key = config.account_key
		self.credential = config.get_credentials()
		self.service = TableServiceClient(credential=self.credential, endpoint=config.table_endpoint)

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



