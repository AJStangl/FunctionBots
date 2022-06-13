import json
import logging
from datetime import datetime

import azure.functions as func
from azure.storage.queue import QueueServiceClient, QueueClient, QueueMessage

from shared_code.database.repository import DataRepository
from shared_code.database.table_model import TableRecord, TableHelper
from shared_code.generators.text.model_text_generator import ModelTextGenerator
from shared_code.services.reply_service import ReplyService
from shared_code.storage_proxies.service_proxy import QueueServiceProxy


def main(genTimer: func.TimerRequest, responseMessage: func.Out[str]) -> None:

	logging.debug(f":: Text Generation Timer Trigger Called")

	reply_service: ReplyService = ReplyService()

	queue_service: QueueServiceClient = QueueServiceProxy().service

	repository: DataRepository = DataRepository()

	queue_client: QueueClient = queue_service.get_queue_client("worker-1")

	if len(queue_client.peek_messages()) == 0:
		logging.debug(":: No New Messages")
		return

	message: QueueMessage = queue_client.receive_message()

	if message.dequeue_count > 3:
		queue_client.delete_message(message)

	incoming_message: TableRecord = TableHelper.handle_incoming_message(message)

	bot_name = incoming_message["RespondingBot"]

	prompt = incoming_message["TextGenerationPrompt"]

	logging.debug(f":: Trigger For Model Generation called at {datetime.now()} for {bot_name}")

	model_generator = ModelTextGenerator()

	result = model_generator.generate_text(bot_name, prompt)

	entity = repository.get_entity_by_id(incoming_message["Id"])

	entity.TextGenerationPrompt = prompt

	entity.TextGenerationResponse = result

	repository.update_entity(entity)

	queue_client.delete_message(message)

	responseMessage.set(json.dumps(entity.as_dict()))

	reply_service.invoke()
