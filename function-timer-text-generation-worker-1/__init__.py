import base64
import json
import logging
from datetime import datetime

import azure.functions as func
from azure.data.tables import TableServiceClient, TableClient
from azure.storage.queue import QueueServiceClient, QueueClient

from shared_code.generators.text.model_text_generator import ModelTextGenerator
from shared_code.models.table_data import TableRecord
from shared_code.storage_proxies.service_proxy import QueueServiceProxy
from shared_code.storage_proxies.table_proxy import TableServiceProxy


async def main(genTimer: func.TimerRequest, responseMessage: func.Out[str]) -> None:
	logging.debug(f":: Text Generation Timer Trigger Called")

	queue_service: QueueServiceClient = QueueServiceProxy().service
	table_service: TableServiceClient = TableServiceProxy().service

	queue_client: QueueClient = queue_service.get_queue_client("worker-1")
	table_client: TableClient = table_service.get_table_client("tracking")

	if len(queue_client.peek_messages()) == 0:
		logging.debug(":: No New Messages")
		return

	message = queue_client.receive_message()

	incoming_message: TableRecord = handle_incoming_message(message)

	bot_name = incoming_message.responding_bot

	prompt = incoming_message.text_generation_prompt

	logging.debug(f":: Trigger For Model Generation called at {datetime.now()} for {bot_name}")

	model_generator = ModelTextGenerator()

	result = model_generator.generate_text(bot_name, prompt)

	entity = table_client.get_entity(partition_key=incoming_message.PartitionKey, row_key=incoming_message.RowKey)

	entity["text_generation_prompt"] = prompt

	entity["text_generation_response"] = result

	table_client.update_entity(entity)

	queue_client.delete_message(message)

	queue_client.close()

	responseMessage.set(json.dumps(entity))


def handle_incoming_message(message) -> TableRecord:
	try:
		incoming_message: TableRecord = json.loads(base64.b64decode(message.content), object_hook=lambda d: TableRecord(**d))
		return incoming_message
	except Exception:
		incoming_message: TableRecord = json.loads(message.content, object_hook=lambda d: TableRecord(**d))
		return incoming_message

