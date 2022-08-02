import logging

import azure.functions as func
import torch.cuda

from shared_code.services.text_generation import TextGenerationService


async def main(message: func.QueueMessage, responseMessage: func.Out[str]) -> None:
	logging.info(f":: Text Response Generation Invocation Worker - 2")
	service: TextGenerationService = TextGenerationService()
	devices = [i for i in range(torch.cuda.device_count())]

	result = service.invoke(message, cuda_device=devices[1])
	responseMessage.set(result)
