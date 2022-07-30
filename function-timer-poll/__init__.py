import logging
import os
import time
import typing
from datetime import datetime

import azure.functions as func
from asyncpraw.models import Comment, Submission
from sqlalchemy.orm import Session

from shared_code.database.context import Context
from shared_code.database.entities import TrackingSubmission, TrackingComment, TrackingResponse
from shared_code.helpers.merge_async_iterator import MergeAsyncIterator
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.models.bot_configuration import BotConfigurationManager, BotConfiguration


async def main(initializingTimer: func.TimerRequest) -> None:
	logging.info(f":: Starting Poll For Reddit Streams {initializingTimer}")
	bot_names: [BotConfiguration] = BotConfigurationManager().get_bot_name_list()
	instance = RedditManager.get_praw_instance_for_bot("PabloBot-GPT2")

	subreddit = await instance.subreddit("CoopAndPabloPlayHouse")
	context: Context = Context()
	comment_stream = subreddit.stream.comments()
	submission_stream = subreddit.stream.submissions()
	time_out_for_iteration: float = float(os.environ["TimeoutForSearchIterator"])

	logging.info(f":: Streaming Comments For {time_out_for_iteration} seconds")
	start_time = time.time()
	async for praw_item in MergeAsyncIterator(submission_stream, comment_stream, time_out=time_out_for_iteration):
		if praw_item is None:
			break

		if isinstance(praw_item, Comment):
			logging.debug(f":: Handling Comment {praw_item} from stream")
			comment: Comment = praw_item
			await add_comment_to_table(comment, context, bot_names)

		if isinstance(praw_item, Submission):
			logging.debug(f":: Handling Submission {praw_item} from stream")
			submission: Submission = praw_item
			await add_submission_to_table(submission, context, bot_names)

	end_time = time.time()
	duration = round(end_time - start_time, 1)
	logging.info(f":: Total Duration for Processing: {duration}...Process Complete")
	await instance.close()
	return None


async def add_submission_to_table(submission: Submission, context: Context, bots: [BotConfiguration]) -> typing.Union[TrackingSubmission, None]:
	session = context.get_session()
	entity = TrackingSubmission()
	entity.Id = submission.id
	entity.Text = tag_submission(submission)
	entity.SubmissionTimestamp = datetime.fromtimestamp(submission.created_utc)
	entity.Subreddit = submission.subreddit.display_name
	entity.Author = getattr(submission.author, 'name', '')
	entity.DateCreated = datetime.now()
	entity.DateUpdated = datetime.now()
	result = context.add(entity, session)
	if result is None:
		logging.info(f":: Added {type(submission)} To Table for {submission.id}")
		# Create Entry For Tracking Comment Responses.
		for bot in bots:
			if bot == entity.Author:
				continue
			tracking_response = TrackingResponse()
			tracking_response.Id = f"{bot}|{entity.Id}"
			tracking_response.BotName = bot
			tracking_response.RedditId = entity.Id,
			tracking_response.HasResponded = False
			tracking_response.InitialTimeSubmitted = datetime.fromtimestamp(submission.created_utc)
			tracking_response.DateCreated = datetime.now()
			tracking_response.DateUpdated = datetime.now()
			tracking_response.Ignore = False
			context.add(tracking_response, session)
		context.close_and_dispose(session)
		return entity

	context.close_and_dispose(session)


async def add_comment_to_table(comment: Comment, context: Context, bots: [BotConfiguration]) -> typing.Union[TrackingComment, None]:
	session: Session = context.get_session()
	entity = TrackingComment()
	entity.Id = comment.id
	entity.SubmissionId = comment.submission.id
	entity.CommentTimestamp = datetime.fromtimestamp(comment.created_utc)
	entity.Author = getattr(comment.author, 'name', '')
	entity.ParentId = comment.parent_id
	entity.Text = ""
	entity.DateCreated = datetime.now()
	entity.DateUpdated = datetime.now()
	result = context.add(entity, session)
	if result is None:
		logging.info(f":: Added {type(comment)} To Table for {comment.id}")
		for bot in bots:
			if bot == entity.Author:
				continue
			tracking_response = TrackingResponse()
			tracking_response.Id = f"{bot}|{entity.Id}"
			tracking_response.BotName = bot
			tracking_response.RedditId = entity.Id,
			tracking_response.HasResponded = False
			tracking_response.InitialTimeSubmitted = datetime.fromtimestamp(comment.created_utc)
			tracking_response.DateCreated = datetime.now()
			tracking_response.DateUpdated = datetime.now()
			tracking_response.Ignore = False
			context.add(tracking_response, session)
		context.close_and_dispose(session)
		return entity
	context.close_and_dispose(session)
	return None


def tag_submission(submission: Submission, tag_override: str = os.environ["SubNameOverride"]) -> str:
	tagged_text = ""
	if not isinstance(submission, Submission):
		return tagged_text

	if submission.is_self:
		tagged_text += "<|soss"
	else:
		tagged_text += "<|sols"

	if tag_override is not None:
		tagged_text += f" r/{tag_override}|>"
	else:
		tagged_text += f" r/{submission.subreddit}|>"

	# prepend the tagged text
	if submission.is_self:

		selftext = submission.selftext

		if hasattr(submission, 'poll_data'):
			for option in submission.poll_data.options:
				selftext += f" - {option.text}"

		# selftext submission
		tagged_text += f"<|sot|>{submission.title}<|eot|><|sost|>{selftext}<|eost|>"

	else:
		# it's a link submission
		tagged_text += f"<|sot|>{submission.title}<|eot|><|sol|><|eol|>"

	return tagged_text




