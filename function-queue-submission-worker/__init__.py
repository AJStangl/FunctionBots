import asyncio
import logging

import azure.functions as func

from shared_code.helpers.record_helper import TableHelper
from shared_code.models.bot_configuration import BotConfiguration
from shared_code.services.new_submission_service import SubmissionService


async def main(message: func.QueueMessage) -> None:
	logging.info(f":: Submission Generation Invocation Worker")
	message_json = TableHelper.handle_message_generic(message)
	bot_config = BotConfiguration(Name=message_json["Name"], Model=message_json["Model"], SubReddits=[message_json["SubReddit"]])
	submission_service: SubmissionService = SubmissionService()
	await submission_service.invoke(bot_config)
