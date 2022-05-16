import json
import logging
import datetime
import azure.functions as func
import logging
import time
from simpletransformers.language_generation import LanguageGenerationModel
from shared_code.models.table_data import TableRecord
from shared_code.storage_proxies.table_proxy import TableServiceProxy


def main(message: func.QueueMessage, responseMessage: func.Out[str]) -> None:

	logging.info(f":: Trigger For Model Generation called at {datetime.date.today()}")

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

class ModelTextGenerator(object):
	def __init__(self):
		self.default_text_generation_parameters = {
			'max_length': 512,
			'num_return_sequences': 1,
			'prompt': None,
			'temperature': 0.8,
			'top_k': 40,
			'repetition_penalty': 1.008,
			'stop_token': '<|endoftext|>',
		}

	def generate_text(self, bot_username, prompt) -> str:

		model = LanguageGenerationModel("gpt2", "D:\\models\\large_larissa_bot", use_cuda=False)

		start_time = time.time()

		# pop the prompt out from the args
		output_list = model.generate(prompt=prompt, args=self.default_text_generation_parameters)

		end_time = time.time()
		duration = round(end_time - start_time, 1)

		logging.info(f'{len(output_list)} sample(s) of text generated in {duration} seconds.')

		if output_list:
			return output_list[0]