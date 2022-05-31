import json
import logging
import typing
from typing import Optional

import azure.functions as func
from praw.models.reddit.base import RedditBase
from praw.reddit import Redditor, Reddit

from shared_code.helpers.reddit_helper import RedditManager
from shared_code.models.table_data import TableRecord
from shared_code.storage_proxies.table_proxy import TableServiceProxy
from shared_code.models.bot_configuration import BotConfiguration

from datetime import timezone
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

	submissions = subreddit.stream.submissions(pause_after=0, skip_existing=False)

	unsorted_submissions = []
	for submission in submissions:
		if submission is None:
			break
		m = process_thing(submission, user, "Submission", table_proxy, reddit_helper)
		if m is not None:
			unsorted_submissions.append(m)

	logging.info(f":: Processing Stream For comments for {bot_name}")
	comments = subreddit.stream.comments(pause_after=0, skip_existing=False)

	unsorted_comments = []
	for comment in comments:
		if comment is None:
			break
		m = process_thing(comment, user, "Comment", table_proxy, reddit_helper)
		if m is not None:
			unsorted_comments.append(m)

	sorted_comments = sorted(unsorted_comments, key=lambda x: x.content_date_submitted_utc)
	sorted_submissions = sorted(unsorted_submissions, key=lambda x: x.content_date_submitted_utc)

	entries_to_write = sorted_submissions + sorted_comments
	objects_written = []
	for item in entries_to_write:
		entity = table_proxy.create_update_entity(item)
		objects_written.append(entity)

	logging.debug(f":: Process Complete, no new inputs from stream {len(objects_written)}")
	return


def process_thing(thing: RedditBase, user: Redditor, input_type: str, proxy: TableServiceProxy, helper: RedditManager) -> Optional[TableRecord]:
	mapped_input: TableRecord = helper.map_base_to_message(thing, user.name, input_type)

	# Filter Out Where responding bot is the author
	if mapped_input.responding_bot == mapped_input.author:
		return None

	hours_since_response = should_respond(mapped_input.content_date_submitted_utc)
	if 24 < hours_since_response:
		logging.info(f":: {mapped_input.input_type} to old {mapped_input.id}")
		return None

	if proxy.entity_exists(mapped_input):
		return None

	else:
		return mapped_input


def should_respond(utc_timestamp):
	return (datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(utc_timestamp)).total_seconds() / 3600
