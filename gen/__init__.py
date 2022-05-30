import base64
import json
import logging
from datetime import datetime

import azure.functions as func

from shared_code.generators.text.model_text_generator import ModelTextGenerator
from shared_code.models.table_data import TableRecord
from shared_code.storage_proxies.service_proxy import QueueServiceProxy
from shared_code.storage_proxies.table_proxy import TableServiceProxy


def main(genTimer: func.TimerRequest, responseMessage: func.Out[str]) -> None:
	logging.debug(f":: Text Generation Timer Trigger Called")

	client = QueueServiceProxy().service.get_queue_client("prompt-queue")

	message = client.receive_message()

	client.delete_message(message)

	client.close()

	message_json = base64.b64decode(message.content).decode('utf-8')

	incoming_message = json.loads(message_json, object_hook=lambda d: TableRecord(**d))

	bot_name = incoming_message.responding_bot

	prompt = incoming_message.text_generation_prompt

	logging.debug(f":: Trigger For Model Generation called at {datetime.now()} for {bot_name}")

	model_generator = ModelTextGenerator()

	result = model_generator.generate_text(bot_name, prompt)

	service = TableServiceProxy().service

	client = service.get_table_client("tracking")

	entity = client.get_entity(partition_key=incoming_message.PartitionKey, row_key=incoming_message.RowKey)

	entity["text_generation_prompt"] = prompt

	entity["text_generation_response"] = result[0]

	client.update_entity(entity)

	responseMessage.set(json.dumps(entity))