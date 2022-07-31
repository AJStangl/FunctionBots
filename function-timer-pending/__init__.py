import logging
import os
import random
import typing

import azure.functions as func
from asyncpraw import Reddit
from asyncpraw.models import Comment, Submission
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from shared_code.database.context import Context
from shared_code.database.entities import TrackingSubmission, TrackingComment, TrackingResponse
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.models.bot_configuration import BotConfigurationManager
from shared_code.models.text_generation_message import TextGenerationMessage


async def main(initializingTimer: func.TimerRequest, msg: func.Out[typing.List[str]]) -> None:
	instance = None
	logging.info(f":: Starting Query For Pending Comments And Submissions {initializingTimer}")

	context: Context = Context()
	session: Session = context.get_session()
	bot_configuration_manager: BotConfigurationManager = BotConfigurationManager()
	messages = []

	try:
		for bot_configuration in bot_configuration_manager.get_configuration():
			bot_name = bot_configuration.Name
			instance: Reddit = RedditManager().get_praw_instance_for_bot(bot_name)

			statement = select(TrackingResponse)\
				.join(TrackingSubmission, TrackingSubmission.Id == TrackingResponse.RedditId)\
				.where(TrackingResponse.HasResponded == False)\
				.where(TrackingResponse.BotName == bot_name)\
				.order_by(desc(TrackingResponse.DateCreated))\
				.limit(100)

			submission_result = list(session.scalars(statement))
			logging.info(f":: Processing Pending Submissions for {bot_name}: {len(submission_result)}")
			for pending_submission in submission_result:
				entity = session.get(TrackingResponse, pending_submission.Id)
				entity.InFlight = True
				session.commit()
				submission_text = pending_submission.Submission.Text
				message: TextGenerationMessage = TextGenerationMessage(reply_id=pending_submission.Id, prompt=submission_text, bot_name=bot_name, reddit_id=pending_submission.Submission.Id, reddit_type="Submission")
				messages.append(message.to_string())

			statement = select(TrackingResponse)\
				.join(TrackingComment, TrackingComment.Id == TrackingResponse.RedditId) \
				.where(TrackingResponse.Ignore == False) \
				.where(TrackingResponse.HasResponded == False)\
				.where(TrackingResponse.Text == None)\
				.where(TrackingComment.Text != "")\
				.where(TrackingResponse.BotName == bot_name)\
				.order_by(desc(TrackingResponse.DateCreated))\
				.limit(60)

			comment_result: [TrackingResponse] = list(session.scalars(statement))
			logging.info(f":: Processing Pending Comments for {bot_name}: {len(comment_result)}")
			for pending_comment in comment_result:
				entity = session.get(TrackingResponse, pending_comment.Id)

				probability_to_reply = random.randint(0, 100)
				if probability_to_reply < 75:
					logging.debug(f":: Random Probability for Processing is {probability_to_reply} but needed < {90}")
					entity.Ignore = True
					session.commit()
					continue
				comment: Comment = await instance.comment(id=pending_comment.RedditId)
				submission: Submission = await instance.submission(id=comment.submission.id)

				if submission.num_comments > int(os.environ["MaxComments"]):
					logging.debug(f":: Parent Submission has to many comments")
					entity.Ignore = True
					session.commit()
					continue

				entity.InFlight = True
				session.commit()

				comment_text = pending_comment.Comment.Text
				message: TextGenerationMessage = TextGenerationMessage(reply_id=pending_comment.Id, prompt=comment_text, bot_name=bot_name, reddit_id=pending_comment.Comment.Id, reddit_type="Comment")
				messages.append(message.to_string())

			await instance.close()
	except Exception as e:
		if instance is not None:
			await instance.close()
		return None
	finally:
		logging.info(f":: Setting {len(messages)} to queue")
		msg.set(messages)
		session.close()



