import os
import json

from azure.core.credentials import AzureNamedKeyCredential


class FunctionAppConfiguration(object):
	account_name: str
	account_key: str
	table_endpoint: str
	queue_endpoint: str
	connection_string: str
	is_emulated: bool

	def __init__(self):
		self.account_name: str = os.environ["AccountName"]
		self.account_key: str = os.environ["AccountKey"]
		self.table_endpoint: str = os.environ["TableEndpoint"]
		self.queue_endpoint: str = os.environ["QueueEndpoint"]
		self.connection_string: str = os.environ["ConnectionString"]
		self.is_emulated: bool = os.environ["IsEmulated"] == "True"

	def get_credentials(self) -> AzureNamedKeyCredential:
		return AzureNamedKeyCredential(self.account_name, self.account_key)
