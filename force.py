import asyncio
import logging
import os

from shared_code.helpers.mapping_models import Mapper
from shared_code.models.bot_configuration import BotConfiguration
from shared_code.services.new_submission_service import SubmissionService

os.environ["SubNameOverride"] = "Guster"
async def main() -> None:

	logging.info(f":: Submission Generation Invocation Worker")
	message_json = {
		"Name":"PlayHouseBot-Gpt2",
		"Model": "D:\\models\\super_mega_pablobot\\",
		"SubReddit": "CoopAndPabloPlayHouse"
	}

	bot_config = BotConfiguration(Name=message_json["Name"], Model=message_json["Model"], SubReddits=[message_json["SubReddit"]])
	submission_service: SubmissionService = SubmissionService()
	await submission_service.invoke(bot_config)
	return None


if __name__ == '__main__':
	asyncio.run(main())