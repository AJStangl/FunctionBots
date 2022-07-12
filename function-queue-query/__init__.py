import asyncio
import logging

import azure.functions as func

from shared_code.services.main_run_service import BotMonitorService


async def main(message: func.QueueMessage) -> None:
	logging.info(f":: Starting BotMonitorService")
	bot_run_service: BotMonitorService = BotMonitorService()
	await bot_run_service.invoke_data_query(message)
	return None
