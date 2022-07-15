import asyncio
import logging

import azure.functions as func

from shared_code.services.main_run_service import BotMonitorService


async def main(message: func.QueueMessage) -> None:
	bot_run_service: BotMonitorService = BotMonitorService()
	eventloop = asyncio.get_event_loop()
	tasks = [
		asyncio.create_task(
			await eventloop.run_in_executor(
				None,
				bot_run_service.invoke_reddit_polling,
				message
			)
		)
	]
	await asyncio.wait(tasks)
	return None
