import json
import logging
from typing import Optional

import azure.functions as func
from praw.models import Submission
from praw.models.reddit.base import RedditBase
from praw.reddit import Redditor, Reddit, Comment

from shared_code.helpers.reddit_helper import RedditManager
from shared_code.models.table_data import TableRecord
from shared_code.storage_proxies.table_proxy import TableServiceProxy
from shared_code.models.bot_configuration import BotConfiguration

import datetime


def main(message: func.QueueMessage) -> None:
	logging.debug(f":: Trigger For Polling Comment/Submission called at {datetime.date.today()}")

	reddit_helper: RedditManager = RedditManager()

	table_proxy: TableServiceProxy = TableServiceProxy()

	message_json = message.get_body().decode('utf-8')

	incoming_message: BotConfiguration = json.loads(message_json, object_hook=lambda d: BotConfiguration(**d))

	bot_name = incoming_message.Name

	reddit: Reddit = reddit_helper.get_praw_instance_for_bot(bot_name)

	user = reddit.user.me()

	logging.debug(f":: Polling For Submissions for User: {user.name}")

	subs = reddit_helper.get_subs_from_configuration(bot_name)

	subreddit = reddit.subreddit(subs)

	unsorted_submissions = []

	unsorted_comments = []

	# submissions: [Submission] = subreddit.new(limit=10)
	submissions = subreddit.stream.submissions(pause_after=0, skip_existing=False)
	comments = subreddit.stream.comments(pause_after=0, skip_existing=False)
	for submission in submissions:
		if submission is None:
			break
		else:
			if submission.num_comments > 200:
				logging.info(f":: Submission Has More Than {200} replies, skipping")
				continue

			if submission.locked:
				logging.info(f":: The Submission is locked. Skipping")
				continue

			m: TableRecord = handle_submission(submission, user, table_proxy, reddit_helper)
			if m is not None:
				unsorted_submissions.insert(0, m)

	for comment in comments:
		if comment is None:
			break

		m = handle_comment(comment, user, table_proxy, reddit_helper)
		if m is not None:
			unsorted_comments.insert(0, m)

	entries_to_write = unsorted_submissions + unsorted_comments

	objects_written = []
	for item in entries_to_write:
		entity = table_proxy.create_update_entity(item)
		objects_written.insert(0, entity)

	logging.info(f":: Complete,Messages Sent - {len(objects_written)} for {bot_name}")


def handle_submission(thing: Submission, user: Redditor, proxy: TableServiceProxy, helper: RedditManager) -> Optional[TableRecord]:
	mapped_input: TableRecord = helper.map_base_to_message(thing, user.name, "Submission")

	# Filter Out Where responding bot is the author
	if mapped_input.responding_bot == mapped_input.author:
		return None

	if timestamp_to_hours(thing.created_utc) > 12:
		logging.info(f":: {mapped_input.input_type} to old {mapped_input.id}")
		return None

	if proxy.entity_exists(mapped_input):
		return None

	else:
		return mapped_input


def handle_comment(comment: Comment, user: Redditor, proxy: TableServiceProxy, helper: RedditManager) -> Optional[TableRecord]:
	mapped_input: TableRecord = helper.map_base_to_message(comment, user.name, "Comment")

	if mapped_input.responding_bot == mapped_input.author:
		return None

	if proxy.entity_exists(mapped_input):
		return None

	if comment.submission.num_comments > 200:
		logging.info(f":: Submission for Comment Has To Many Replies {comment.submission.num_comments}")
		return None

	comment_created_hours = timestamp_to_hours(comment.created_utc)

	submission_created_hours = timestamp_to_hours(comment.submission.created_utc)

	delta = abs(comment_created_hours - submission_created_hours)

	if delta > 2:
		logging.info(f":: Time between comment and reply is {delta} > 2 hours...Skipping")
		return None

	if comment.submission.locked:
		logging.info(f":: Comment is locked! Skipping...")
		return None
	else:
		return mapped_input


def timestamp_to_hours(utc_timestamp):
	return (datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(utc_timestamp)).total_seconds() / 3600
