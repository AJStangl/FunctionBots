import json
import logging

import azure.functions as func

from shared_code.queue_utility.table_proxy import TableServiceProxy


def main(message: func.QueueMessage) -> None:
	message_json = message.get_body().decode('utf-8')

	message_json = json.loads(message_json)

	logging.info(message_json)


	service = TableServiceProxy().service
	client = service.get_table_client("tracking")

	entity = client.get_entity(partition_key=message_json["partition_key"], row_key=message_json["row_key"])
	client.delete_entity(entity)

