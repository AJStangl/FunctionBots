import datetime
import json
import logging
from typing import Optional

from azure.core.exceptions import HttpResponseError
from azure.data.tables import TableServiceClient, TableClient
from azure.data.tables import TableEntity
from shared_code.models.azure_configuration import FunctionAppConfiguration
from shared_code.models.table_data import TableRecord


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

	def create_update_entity(self, entity: TableRecord) -> Optional[TableEntity]:
		client = self.get_client()
		try:
			return client.get_entity(partition_key=entity.PartitionKey, row_key=entity.RowKey)
		except HttpResponseError:
			logging.info(f":: Creating new record for {entity.PartitionKey} - {entity.RowKey}")
			client.create_entity(entity=json.loads(entity.json))
			return client.get_entity(partition_key=entity.PartitionKey, row_key=entity.RowKey)
		finally:
			client.close()

	def ensure_created(self, table_name) -> None:
		logging.info(f":: Creating Table {table_name}")
		self.service.create_table_if_not_exists("tracking")
		return None

	def clear_table(self) -> None:
		client = self.get_client()

		query_filter = f"Timestamp lt datetime'{datetime.datetime.now().isoformat()}'"

		entities = client.query_entities(query_filter=query_filter)

		for entity in entities:
			client.delete_entity(entity)

		return None