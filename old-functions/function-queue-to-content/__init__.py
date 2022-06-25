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
from shared_code.database.instance import TableRecord, TableHelper
from shared_code.models.bot_configuration import BotConfiguration
import datetime

def main(message: func.QueueMessage) -> None:

	reddit_helper: RedditManager = RedditManager()

	repository: DataRepository = DataRepository()

	message_json = message.get_body().decode('utf-8')

	incoming_message: BotConfiguration = json.loads(json.dumps(message_json),object_hook=lambda d: BotConfiguration(**d))

	bot_name = incoming_message.Name

	reddit = reddit_helper.get_praw_instance_for_bot(bot_name)

	user = reddit.user.me()

	subs = reddit_helper.get_subs_from_configuration(bot_name)

	subreddit = reddit.subreddit(subs)

	submissions: [Submission] = subreddit.stream.submissions(pause_after=0)

	comments: [Comment] = subreddit.stream.comments(pause_after=0)

	for elem in chain_listing_generators(submissions, comments):
		if isinstance(elem, Submission):
			handle_submission(elem, user, repository)
		if isinstance(elem, Comment):
			handle_comment(elem, user, repository, reddit_helper)




def handle_submission(thing: Submission, user: Redditor, repository: DataRepository) -> Optional[TableRecord]:
	# thing, user.name, "Submission"
	mapped_input: TableRecord = TableHelper.map_base_to_message(
		reddit_id=thing.id,
		sub_reddit=thing.subreddit.display_name,
		input_type="Submission",
		time_in_hours=timestamp_to_hours(thing.created),
		submitted_date=thing.created,
		author=getattr(thing.author, 'name', ''),
		responding_bot=user.name
	)

	# Filter Out Where responding bot is the author
	if mapped_input.RespondingBot == mapped_input.Author:
		return None

	if timestamp_to_hours(thing.created_utc) > 12:
		logging.info(f":: {mapped_input.InputType} to old {mapped_input.Id} for {user.name}")
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
		responding_bot=user.name,
		time_in_hours=timestamp_to_hours(comment.created)
	)

	if mapped_input.RespondingBot == mapped_input.Author:
		return None

	sub_id = comment.submission.id

	instance = helper.get_praw_instance_for_bot(user.name)

	sub = instance.submission(id=sub_id)

	if sub.num_comments > int(os.environ["MaxComments"]):
		logging.info(f":: Submission for Comment Has To Many Replies {comment.submission.num_comments} for {user.name}")
		return None

	comment_created_hours = timestamp_to_hours(comment.created_utc)

	submission_created_hours = timestamp_to_hours(sub.created_utc)

	delta = abs(comment_created_hours - submission_created_hours)

	max_comment_submission_diff = int(os.environ["MaxCommentSubmissionTimeDifference"])

	if delta > int(os.environ["MaxCommentSubmissionTimeDifference"]):
		logging.info(
			f":: Time between comment and reply is {delta} > {max_comment_submission_diff} hours for {user.name}|{comment.id}")
		return None

	if comment.submission.locked:
		logging.info(f":: Comment is locked! Skipping...")
		return None
	else:
		entity = repository.create_if_not_exist(mapped_input)
		return entity


def timestamp_to_hours(utc_timestamp):
	return int((datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(utc_timestamp)).total_seconds() / 3600)


def chain_listing_generators(*iterables):
	# Special tool for chaining PRAW's listing generators
	# It joins the three iterables together so that we can DRY
	for it in iterables:
		for element in it:
			if element is None:
				break
			else:
				yield element
