import json
import logging
from typing import Optional

import azure.functions as func

from shared_code.database.table_record import TableRecord
from shared_code.generators.text.model_text_generator import ModelTextGenerator
from shared_code.helpers.record_helper import TableHelper
from shared_code.services.service_container import ServiceContainer


class TextGenerationService(ServiceContainer):
	def __init__(self):
		super().__init__()

	def invoke(self, message: func.QueueMessage) -> Optional[str]:
		logging.info(f"Invoking Text Generation for Message ID: {message.id}")
		incoming_message: TableRecord = TableHelper.handle_fucking_bullshit(message)

		bot_name = incoming_message["RespondingBot"]

		entity = self.repository.get_entity_by_id(incoming_message["Id"])

		if entity is None:
			logging.info(f":: Entity Not Found For Id {incoming_message['Id']}")
			return None

		prompt = incoming_message["TextGenerationPrompt"]

		model_text_generator: ModelTextGenerator = ModelTextGenerator()

		result = model_text_generator.generate_text_with_no_wrapper(bot_name, prompt)

		entity.TextGenerationPrompt = prompt

		entity.TextGenerationResponse = result

		self.repository.update_entity(entity)

		return json.dumps(entity.as_dict())
