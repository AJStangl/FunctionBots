import json
import logging
from shared_code.generators.text.model_text_generator import ModelTextGenerator
import azure.functions as func

from shared_code.queue_utility.table_proxy import TableServiceProxy


def main(message: func.QueueMessage) -> None:
	message_json = message.get_body().decode('utf-8')

	message_json = json.loads(message_json)

	partition_key = message_json["partition_key"]
	split_key = partition_key.split("|")
	bot_name = split_key[1]
	prompt = message_json["text_generation_prompt"]
	model_generator = ModelTextGenerator()
	result = model_generator.generate_text(bot_name, prompt)

	service = TableServiceProxy().service
	client = service.get_table_client("tracking")

	entity = client.get_entity(partition_key=message_json["partition_key"], row_key=message_json["row_key"])

	entity["text_generation_prompt"] = prompt
	entity["text_generation_response"] = result
	client.update_entity(entity)



