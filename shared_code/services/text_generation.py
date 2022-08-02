import json
import logging
from typing import Optional

import azure.functions as func
from sqlalchemy.orm import Session

from shared_code.database.table_record import TableRecord
from shared_code.generators.text.model_text_generator import ModelTextGenerator
from shared_code.helpers.mapping_models import Mapper
from shared_code.services.service_container import ServiceContainer


class TextGenerationService(ServiceContainer):
	def __init__(self):
		super().__init__()

	def invoke(self, message: func.QueueMessage, cuda_device=0) -> Optional[str]:
		session: Session = self.repository.get_session()
		try:
			logging.info(f"Invoking Text Generation for Message ID: {message.id}")
			incoming_message: TableRecord = Mapper.handle_fucking_bullshit(message)

			bot_name = incoming_message["RespondingBot"]

			entity = self.repository.get_by_id_with_session(session, incoming_message["Id"])

			if entity is None:
				logging.info(f":: Entity Not Found For Id {incoming_message['Id']}")
				return None

			prompt = incoming_message["TextGenerationPrompt"]

			model_text_generator: ModelTextGenerator = ModelTextGenerator()

			result = model_text_generator.generate_text_with_no_wrapper(bot_name, prompt, cuda_device=cuda_device)

			entity.TextGenerationPrompt = prompt

			entity.TextGenerationResponse = result

			session.commit()

			foo = {
				"Id": entity.Id,
				"RedditId": entity.RedditId,
				"Subreddit": entity.Subreddit,
				"InputType": entity.InputType,
				"Author": entity.Author,
				"RespondingBot": entity.RespondingBot,
				"TextGenerationPrompt": entity.TextGenerationPrompt,
				"TextGenerationResponse": entity.TextGenerationResponse,
				"HasResponded": entity.HasResponded,
				"Status": entity.Status,
				"ReplyProbability": entity.ReplyProbability,
				"Url": entity.Url
			}

			return json.dumps(foo)
		finally:
			session.close()
