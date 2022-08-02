import azure.functions as func

from shared_code.services.invoke_reddit_polling import InvokePollingService


async def main(message: func.QueueMessage) -> None:
	polling_service: InvokePollingService = InvokePollingService()
	await polling_service.invoke_reddit_polling(message)
	return None
