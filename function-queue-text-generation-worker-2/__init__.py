import logging

import azure.functions as func

from shared_code.database.repository import DataRepository
from shared_code.generators.text.model_text_generator import ModelTextGenerator
from shared_code.services.text_generation import TextGenerationService


async def main(message: func.QueueMessage, responseMessage: func.Out[str]) -> None:
	logging.info(f":: Text Response Generation Invocation Worker - 2")
	result = TextGenerationService().invoke(message)
	responseMessage.set(result)
