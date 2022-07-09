import logging
import azure.functions as func
import random

from shared_code.models.bot_configuration import BotConfigurationManager, BotConfiguration
from shared_code.services.new_submission_service import SubmissionService


async def main(submissionTimer: func.TimerRequest) -> None:
	logging.info(f":: Submission Creation Trigger Called")
	submission_service: SubmissionService = SubmissionService()
	manager: BotConfigurationManager = BotConfigurationManager()
	configs: [BotConfiguration] = list(filter(manager.filter_configuration, manager.get_configuration()))
	random.shuffle(configs)

	for bot_config in configs:
		successful: bool = await submission_service.invoke(bot_configuration=bot_config)
		if successful:
			break
		else:
			continue
	return None
