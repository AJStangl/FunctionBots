import json
import logging
import os
import typing
from typing import Optional

import azure.functions as func
from praw.models import Submission
from praw.reddit import Redditor, Reddit, Comment

from shared_code.helpers.reddit_helper import RedditManager
from shared_code.database.repository import DataRepository
from shared_code.database.table_model import TableRecord, TableHelper
from shared_code.models.bot_configuration import BotConfiguration
import datetime

def main(message: func.QueueMessage, msg: func.Out[str]) -> None:
	logging.info(f":: Trigger For Polling Comment/Submission called at {datetime.date.today()}")

	reddit_helper: RedditManager = RedditManager()

	repository: DataRepository = DataRepository()

	message_json = message.get_body().decode('utf-8')

	incoming_message: BotConfiguration = json.loads(message_json, object_hook=lambda d: BotConfiguration(**d))

	bot_name = incoming_message.Name

	reddit: Reddit = reddit_helper.get_praw_instance_for_bot(bot_name)

	user = reddit.user.me()

	logging.debug(f":: Polling For Submissions for User: {user.name}")

	subs = reddit_helper.get_subs_from_configuration(bot_name)

	subreddit = reddit.subreddit(subs)

	submissions = subreddit.stream.submissions(pause_after=0, skip_existing=False)
	for submission in submissions:
		if submission is None:
			break
		else:
			max_comments = int(os.environ["MaxComments"])
			if submission.num_comments > int(max_comments):
				logging.info(f":: Submission Has More Than {max_comments} replies, skipping")
				continue

			if submission.locked:
				logging.info(f":: The Submission is locked. Skipping")
				continue

			handle_submission(submission, user, repository)

	comments = subreddit.stream.comments(pause_after=0, skip_existing=False)
	for comment in comments:
		if comment is None:
			break

		handle_comment(comment, user, repository, reddit_helper)

	msg.set(message_json)

	return None



def handle_submission(thing: Submission, user: Redditor, repository: DataRepository) -> Optional[TableRecord]:
	# thing, user.name, "Submission"
	mapped_input: TableRecord = TableHelper.map_base_to_message(
		reddit_id=thing.id,
		sub_reddit=thing.subreddit.display_name,
		input_type="Submission",
		submitted_date=thing.created,
		author=getattr(thing.author, 'name', ''),
		responding_bot=user.name
	)

	# Filter Out Where responding bot is the author
	if mapped_input.RespondingBot == mapped_input.Author:
		return None

	if timestamp_to_hours(thing.created_utc) > 6:
		logging.debug(f":: {mapped_input.InputType} to old {mapped_input.Id}")
		return None

	entity = repository.create_if_not_exist(mapped_input)

	return entity


def handle_comment(comment: Comment, user: Redditor, repository: DataRepository, helper: RedditManager) -> Optional[TableRecord]:
	mapped_input: TableRecord = TableHelper.map_base_to_message(
		reddit_id=comment.id,
		sub_reddit=comment.subreddit.display_name,
		input_type="Comment",
		submitted_date=comment.created,
		author=getattr(comment.author, 'name', ''),
		responding_bot=user.name
	)

	if mapped_input.RespondingBot == mapped_input.Author:
		return None

	sub_id = comment.submission.id

	instance = helper.get_praw_instance_for_bot(user.name)

	sub = instance.submission(id=sub_id)

	if sub.num_comments > int(os.environ["MaxComments"]):
		logging.info(f":: Submission for Comment Has To Many Replies {comment.submission.num_comments}")
		return None

	comment_created_hours = timestamp_to_hours(comment.created_utc)

	submission_created_hours = timestamp_to_hours(sub.created_utc)

	delta = abs(comment_created_hours - submission_created_hours)

	max_comment_submission_diff = int(os.environ["MaxCommentSubmissionTimeDifference"])

	if delta > int(os.environ["MaxCommentSubmissionTimeDifference"]):
		logging.info(f":: Time between comment and reply is {delta} > {max_comment_submission_diff} hours...Skipping")
		return None

	if comment.submission.locked:
		logging.info(f":: Comment is locked! Skipping...")
		return None
	else:
		entity = repository.create_if_not_exist(mapped_input)
		return entity


def timestamp_to_hours(utc_timestamp):
	return (datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(utc_timestamp)).total_seconds() / 3600
