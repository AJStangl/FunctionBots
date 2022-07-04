import logging

import azure.functions as func

from shared_code.database.repository import DataRepository
from shared_code.generators.text.model_text_generator import ModelTextGenerator
from shared_code.services.text_generation import TextGenerationService


async def main(message: func.QueueMessage, responseMessage: func.Out[str]) -> None:
	logging.debug(f":: Text1Response Generation Invocation Worker - 2")
	model_generator: ModelTextGenerator = ModelTextGenerator()
	repository: DataRepository = DataRepository()
	text_gen_service = TextGenerationService(repository, model_generator)
	result = text_gen_service.invoke(message)
	responseMessage.set(result)
