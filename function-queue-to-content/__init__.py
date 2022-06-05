import json
import logging
from typing import Optional
import aiohttp
import azure.functions as func
from asyncpraw.models import Submission
from asyncpraw.models.reddit.base import RedditBase
from asyncpraw.reddit import Redditor, Reddit, Comment

from shared_code.helpers.reddit_helper import RedditManager
from shared_code.models.table_data import TableRecord
from shared_code.storage_proxies.table_proxy import TableServiceProxy
from shared_code.models.bot_configuration import BotConfiguration

import datetime


async def main(message: func.QueueMessage) -> None:
	logging.debug(f":: Trigger For Polling Comment/Submission called at {datetime.date.today()}")

	reddit_helper: RedditManager = RedditManager()

	table_proxy: TableServiceProxy = TableServiceProxy()

	message_json = message.get_body().decode('utf-8')

	incoming_message: BotConfiguration = json.loads(message_json, object_hook=lambda d: BotConfiguration(**d))

	bot_name = incoming_message.Name

	reddit: Reddit = reddit_helper.get_praw_instance_for_bot(bot_name)

	user = await reddit.user.me()

	logging.debug(f":: Polling For Submissions for User: {user.name}")

	subs = reddit_helper.get_subs_from_configuration(bot_name)

	subreddit = await reddit.subreddit(subs)

	unsorted_submissions = []

	unsorted_comments = []

	async for submission in subreddit.stream.submissions():
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

	async for comment in subreddit.stream.comments():
		if comment is None:
			break
		m = await handle_comment(comment, user, table_proxy, reddit_helper, reddit)
		if m is not None:
			unsorted_comments.insert(0, m)

	entries_to_write = unsorted_submissions + unsorted_comments

	objects_written = []
	for item in entries_to_write:
		entity = table_proxy.create_update_entity(item)
		objects_written.insert(0, entity)

	await reddit.close()
	logging.info(f":: Complete,Messages Sent - {len(objects_written)} for {bot_name}. Closing Connection...")


def handle_submission(thing: Submission, user: Redditor, proxy: TableServiceProxy, helper: RedditManager) -> Optional[TableRecord]:
	mapped_input: TableRecord = helper.map_base_to_message(thing, user.name, "Submission")

	# Filter Out Where responding bot is the author
	if mapped_input.responding_bot == mapped_input.author:
		logging.info(f":: Submission Author Is Same As Responding Bot - {mapped_input.responding_bot} skipping...")
		return None

	if timestamp_to_hours(thing.created_utc) > 12:
		logging.info(f":: Submission is older than 12 hours - skipping...")
		return None

	if proxy.entity_exists(mapped_input):
		logging.info(f":: Submission Already exists in table - skipping...")
		return None

	else:
		return mapped_input


async def handle_comment(comment: Comment, user: Redditor, proxy: TableServiceProxy, helper: RedditManager, instance: Reddit) -> Optional[TableRecord]:
	mapped_input: TableRecord = helper.map_base_to_message(comment, user.name, "Comment")

	if mapped_input.responding_bot == mapped_input.author:
		logging.info(f":: Comment Author Is Same As Responding Bot - {mapped_input.responding_bot} skipping...")
		return None

	if proxy.entity_exists(mapped_input):
		logging.info(f":: Comment Already exists in table - skipping...")
		return None

	sub_id = comment.submission.id

	parent_submission = await instance.submission(id=sub_id)

	if parent_submission is None:
		logging.info(":: Parent Submission For Comment did not load - Skipping")
		return None

	if parent_submission.num_comments > 200:
		logging.info(f":: Submission for Comment Has To Many Replies {parent_submission.num_comments} - skipping")
		return None

	comment_created_hours = timestamp_to_hours(comment.created_utc)

	submission_created_hours = timestamp_to_hours(parent_submission.created_utc)

	delta = abs(comment_created_hours - submission_created_hours)

	if delta > 2:
		logging.info(f":: Time between comment and reply is {delta} > 2 hours...Skipping")
		return None

	if parent_submission.locked:
		logging.info(f":: Comment is locked! Skipping...")
		return None
	else:
		return mapped_input


def timestamp_to_hours(utc_timestamp):
	return (datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(utc_timestamp)).total_seconds() / 3600
