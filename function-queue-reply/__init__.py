import logging
from typing import Optional

import azure.functions as func
from asyncpraw import Reddit
from asyncpraw.models import Comment, Submission
from sqlalchemy.orm import Session

from shared_code.database.context import Context
from shared_code.database.entities import TrackingResponse
from shared_code.helpers.record_helper import TableHelper
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.helpers.tagging import Tagging


async def main(message: func.QueueMessage) -> None:
	logging.info(f":: Reply Service Invocation")
	message_json = TableHelper.handle_message_generic(message)
	bot_name: str = message_json['BotName']
	prompt: str = message_json['Prompt']
	response: str = message_json['Response']
	tracking_id: str = message_json['ReplyId']
	reddit_id: str = message_json['RedditId']
	reddit_type: str = message_json['RedditType']
	context: Context = Context()
	session: Session = context.get_session()

	reddit: Reddit = RedditManager().get_praw_instance_for_bot(bot_name)
	tagging: Tagging = Tagging(reddit)

	try:
		tracking_response: TrackingResponse = session.get(TrackingResponse, tracking_id)
		if tracking_response is None:
			logging.info(f":: No entity found with Id {tracking_id}")
			return None

		extract: dict = tagging.extract_reply_from_generated_text(prompt, response)

		response_body = try_get_body(extract)

		if response_body is None:
			logging.info(f":: No body could be extracted from {response} for {prompt}")
			return None

		if reddit_type == "Submission":
			logging.info(f":: Sending Out Reply To Submission - {tracking_response.RedditId}")
			submission_instance: Submission = await reddit.submission(id=tracking_response.RedditId)
			await submission_instance.reply(response_body)
			tracking_response.HasResponded = True
			session.commit()
			logging.info(f":: Reply Complete for {tracking_response.Id}")
			return None

		if reddit_type == "Comment":
			logging.info(f":: Sending Out Reply To Comment - {tracking_response.RedditId}")
			comment_instance: Comment = await reddit.comment(id=tracking_response.RedditId)
			await comment_instance.reply(response_body)
			tracking_response.HasResponded = True
			session.commit()
			logging.info(f":: Reply Complete for {tracking_response.Id}")
			return None

	finally:
		context.close_and_dispose(session)
		await reddit.close()
		return None


def try_get_body(extract: dict) -> Optional[str]:
	try:
		body: str = extract['body']
		return body
	except Exception as e:
		return None
