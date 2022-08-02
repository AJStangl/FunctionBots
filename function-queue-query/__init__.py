import azure.functions as func

from shared_code.services.query_service import QueryService


async def main(message: func.QueueMessage) -> None:
	query_service: QueryService = QueryService()
	await query_service.invoke_data_query(message)
	return None
