import json
import logging

import azure.functions as func

from shared_code.generators.text.model_text_generator import ModelTextGenerator
from shared_code.models.table_data import TableRecord
from shared_code.storage_proxies.table_proxy import TableServiceProxy


def main(message: func.QueueMessage, responseMessage: func.Out[str]) -> None:

	message_json = message.get_body().decode('utf-8')

	incoming_message = json.loads(message_json, object_hook=lambda d: TableRecord(**d))

	model_generator = ModelTextGenerator()

	bot_name = incoming_message.responding_bot

	prompt = incoming_message.text_generation_prompt

	result = model_generator.generate_text(bot_name, prompt)

	service = TableServiceProxy().service

	client = service.get_table_client("tracking")

	entity = client.get_entity(partition_key=incoming_message.PartitionKey, row_key=incoming_message.RowKey)

	entity["text_generation_prompt"] = prompt

	entity["text_generation_response"] = result

	client.update_entity(entity)

	responseMessage.set(json.dumps(entity))
