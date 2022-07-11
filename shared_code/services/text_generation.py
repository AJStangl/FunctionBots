import json
import logging
from datetime import datetime
import azure.functions as func
from shared_code.database.instance import TableRecord
from shared_code.helpers.record_helper import TableHelper
from shared_code.database.repository import DataRepository
from shared_code.generators.text.model_text_generator import ModelTextGenerator


class TextGenerationService:
	def __init__(self, repository_instance: DataRepository, model_generator: ModelTextGenerator):
		self.repository: DataRepository = repository_instance
		self.model_generator: ModelTextGenerator = model_generator

	def invoke(self, message: func.QueueMessage) -> str:
		logging.info(f"Invoking Text Generation for Message ID: {message.id}")
		incoming_message: TableRecord = TableHelper.handle_fucking_bullshit(message)

		bot_name = incoming_message["RespondingBot"]

		entity = self.repository.get_entity_by_id(incoming_message["Id"])

		if entity is None:
			logging.info(f":: Entity Not Found For Id {incoming_message['Id']}")
			return None

		prompt = incoming_message["TextGenerationPrompt"]

		result = self.model_generator.generate_text_with_no_wrapper(bot_name, prompt, num_text_generations=1)

		entity.TextGenerationPrompt = prompt

		entity.TextGenerationResponse = result

		self.repository.update_entity(entity)

		return json.dumps(entity.as_dict())
