import logging
import time
import azure.functions as func
from asyncpraw import Reddit
from asyncpraw.models import Comment, Submission
from sqlalchemy.orm import Session

from shared_code.database.context import Context
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.helpers.tagging import Tagging


async def main(initializingTimer: func.TimerRequest) -> None:
	logging.info(f":: Starting Comment History Collection {initializingTimer}")
	instance: Reddit = RedditManager.get_praw_instance_for_bot("PabloBot-GPT2")
	tagging: Tagging = Tagging(instance)
	context: Context = Context()
	session: Session = context.get_session()
	entities: [] = context.get_comments_for_processing(session, limit=100)

	logging.info(f":: Processing {len(entities)} Comment Text Values")
	comment_ids = []
	time_out_for_iteration = 120
	logging.info(f":: Query for Comments and process for {time_out_for_iteration} seconds")
	start_time = time.time()
	for entity in entities:
		comment_id = entity.Id
		comment_ids.append(comment_id)
		submission_id = entity.SubmissionId
		try:
			comment: Comment = await instance.comment(id=comment_id, fetch=True)
			submission: Submission = await instance.submission(id=submission_id, fetch=True)
			text = await tagging.tag_comment_with_sub(comment, submission)
			entity.Text = text

		except Exception as e:
			logging.error(f":: An error has occurred while attempting to assemble history for {comment_id}")
			continue
		session.commit()

	end_time = time.time()
	duration = round(end_time - start_time, 1)
	logging.info(f":: Total Duration for Processing: {duration}...Process Complete")

	context.close_and_dispose(session)
	await instance.close()

	logging.info(f":: Process Complete For Comment History Collection. Number of comments processed {len(comment_ids)}")
	return None
