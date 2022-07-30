import logging
import typing

import azure.functions as func

from shared_code.models.bot_configuration import BotConfigurationManager
from shared_code.services.initialize_bots import StartService


async def main(initializingTimer: func.TimerRequest, msg: func.Out[typing.List[str]], dataMsg: func.Out[typing.List[str]]) -> None:
	start_service: StartService = StartService()

	messages: [str] = start_service.invoke()

	msg.set(messages)

	dataMsg.set(messages)

	return None
