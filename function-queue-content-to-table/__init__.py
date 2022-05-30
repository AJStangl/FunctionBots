import datetime
import json
import logging

import azure.functions as func

from shared_code.models.table_data import TableRecord
from shared_code.storage_proxies.table_proxy import TableServiceProxy


def main(message: func.QueueMessage) -> None:
	logging.debug(f":: Trigger For Text Prompt Extraction called at {datetime.date.today()}")

	proxy: TableServiceProxy = TableServiceProxy()

	message_json = message.get_body().decode('utf-8')

	incoming_message: TableRecord = json.loads(message_json, object_hook=lambda d: TableRecord(**d))

	proxy.entity_exists(incoming_message)




