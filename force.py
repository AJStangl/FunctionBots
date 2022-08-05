async def main(message:dict) -> None:
	logging.info(f":: Submission Generation Invocation Worker")
	message_json = Mapper.handle_message_generic(message)
	bot_config = BotConfiguration(Name=message_json["Name"], Model=message_json["Model"], SubReddits=[message_json["SubReddit"]])
	submission_service: SubmissionService = SubmissionService()
	await submission_service.invoke(bot_config)
	return None