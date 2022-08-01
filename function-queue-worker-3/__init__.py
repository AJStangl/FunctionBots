import logging

import azure.functions as func
from sqlalchemy.orm import Session

from shared_code.database.context import Context
from shared_code.database.entities import TrackingResponse
from shared_code.generators.text.model_text_generator import ModelTextGenerator
from shared_code.helpers.record_helper import TableHelper
from shared_code.models.reply_message import ReplyMessage
from shared_code.services.text_generation import TextGenerationService


async def main(message: func.QueueMessage, responseMessage: func.Out[str]) -> None:
	message_json = TableHelper.handle_message_generic(message)
	bot_name: str = message_json['BotName']
	prompt: str = message_json['Prompt']
	tracking_id: str = message_json['ReplyId']
	reddit_id: str = message_json['RedditId']
	reddit_type: str = message_json['RedditType']

	context: Context = Context()
	session: Session = context.get_session()
	model_text_generator: ModelTextGenerator = ModelTextGenerator()

	try:
		entity: TrackingResponse = session.get(TrackingResponse, tracking_id)

		if entity is None:
			logging.info(f":: No entity present for Id: {tracking_id}")
			return

		response = model_text_generator.generate_text_with_no_wrapper(bot_name, prompt, device_id="2")

		entity.Text = response

		session.commit()

		reply_message: ReplyMessage = ReplyMessage(bot_name, prompt, response, reddit_type, reddit_id, tracking_id)

		responseMessage.set(reply_message.to_string())

	finally:
		context.close_and_dispose(session)

