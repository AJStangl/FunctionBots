import logging

import azure.functions as func

from shared_code.services.text_generation import TextGenerationService


def main(message: func.QueueMessage, responseMessage: func.Out[str]) -> None:
	logging.info(f":: Text Response Generation Invocation Worker - 3")
	service: TextGenerationService = TextGenerationService()
	result = service.invoke(message)
	responseMessage.set(result)
