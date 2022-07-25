import asyncio
import logging

import azure.functions as func

from shared_code.services.main_run_service import BotMonitorService


async def main(message: func.QueueMessage) -> None:
	bot_run_service: BotMonitorService = BotMonitorService()
	await bot_run_service.invoke_reddit_polling(message)
	return None
