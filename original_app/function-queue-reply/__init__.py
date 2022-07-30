import asyncio
import logging

import azure.functions as func

from shared_code.services.reply_service import ReplyService


async def main(message: func.QueueMessage) -> None:
	logging.info(f":: Reply Service Invocation")
	reply_service: ReplyService = ReplyService()
	await reply_service.handle_message(message)
	# eventloop = asyncio.get_event_loop()
	# tasks = [
	# 	asyncio.create_task(
	# 		await eventloop.run_in_executor(
	# 			None,
	# 			reply_service.handle_message,
	# 			message
	# 		)
	# 	)
	# ]
	# await asyncio.wait(tasks)
	return None
