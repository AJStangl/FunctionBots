import json
import logging
from datetime import datetime

import azure.functions as func

from shared_code.database.instance import TableRecord, TableHelper
from shared_code.database.repository import DataRepository
from shared_code.generators.text.model_text_generator import ModelTextGenerator


def main(message: func.QueueMessage, responseMessage: func.Out[str]) -> None:

	logging.debug(f":: Text Generation Timer Trigger Called")

	repository: DataRepository = DataRepository()

	incoming_message: TableRecord = TableHelper.handle_fucking_bullshit(message)

	bot_name = incoming_message["RespondingBot"]

	prompt = incoming_message["TextGenerationPrompt"]

	logging.debug(f":: Trigger For Model Generation called at {datetime.now()} for {bot_name}")

	model_generator = ModelTextGenerator()

	result = model_generator.generate_text(bot_name, prompt)

	entity = repository.get_entity_by_id(incoming_message["Id"])

	entity.TextGenerationPrompt = prompt

	entity.TextGenerationResponse = result

	repository.update_entity(entity)

	responseMessage.set(json.dumps(entity.as_dict()))
