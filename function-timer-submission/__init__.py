import logging
import random
import typing

import azure.functions as func

from shared_code.models.bot_configuration import BotConfigurationManager, BotConfiguration
from shared_code.services.new_submission_service import SubmissionService


async def main(submissionTimer: func.TimerRequest) -> None:
	logging.info(f":: Submission Creation Trigger Called")
	manager: BotConfigurationManager = BotConfigurationManager()
	service = SubmissionService()
	choice = random.choice(manager.get_configuration())
	await service.invoke(choice)
	return None
