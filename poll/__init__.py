import datetime
import json
import logging
import typing
from typing import Optional

import azure.functions as func
from praw.models.reddit.base import RedditBase
from praw.reddit import Redditor

from shared_code.helpers.reddit_helper import RedditHelper
from shared_code.storage_proxies.table_proxy import TableServiceProxy
from shared_code.models.bot_configuration import BotConfiguration

from datetime import timezone
import datetime


def main(message: func.QueueMessage, msg: func.Out[typing.List[str]]) -> None:
	helper = RedditHelper()

	logging.debug(f":: Trigger For Polling Comment/Submission called at {datetime.date.today()}")

	proxy = TableServiceProxy()

	message_json = message.get_body().decode('utf-8')

	incoming_message = json.loads(message_json, object_hook=lambda d: BotConfiguration(**d))

	bot_name = incoming_message.Name

	reddit = helper.get_praw_instance(bot_name)

	user = reddit.user.me()

	logging.debug(f":: Polling For Submissions for User: {user.name}")

	subs = helper.get_subs_from_configuration(bot_name)

	logging.debug(f":: Obtaining New/Incoming Streams For Subreddit: {subs} - {bot_name}")

	subreddit = reddit.subreddit(subs)

	logging.debug(f":: Subreddit {subreddit} connected. Obtaining Stream for {bot_name}")

	messages = []

	logging.debug(f":: Processing Stream For submissions {bot_name}")
	submissions = subreddit.stream.submissions(pause_after=0, skip_existing=False)
	user_subs = user.submissions.new(limit=20)

	for submission in user_subs:
		if submission is None:
			break
		m = process_thing(submission, user, "Submission", proxy, helper)
		if m is not None:
			messages.append(m)
	for submission in submissions:
		if submission is None:
			break
		m = process_thing(submission, user, "Submission", proxy, helper)
		if m is not None:
			messages.append(m)

	logging.info(f":: Processing Stream For comments for {bot_name}")
	comments = subreddit.stream.comments(pause_after=0, skip_existing=False)
	user_comments = user.comments.new(limit=100)

	for comment in user_comments:
		if comment is None:
			break
		m = process_thing(comment, user, "Comment", proxy, helper)
		if m is not None:
			messages.append(m)
	for comment in comments:
		if comment is None:
			break
		m = process_thing(comment, user, "Comment", proxy, helper)
		if m is not None:
			messages.append(m)

	if len(messages) > 0:
		msg.set(messages)
		logging.debug(f":: Sent Message Batch Successfully from {bot_name}")
		return

	msg.set([])
	logging.debug(f":: Process Complete, no new inputs from stream {bot_name}")
	return


def process_thing(thing: RedditBase, user: Redditor, input_type: str, proxy: TableServiceProxy, helper: RedditHelper) -> Optional[str]:
	mapped_input = helper.map_base_to_message(thing, user.name, input_type)

	# Filter Out Where responding bot is the author
	if mapped_input.responding_bot == mapped_input.author:
		return None

	# Filter existing entities
	if proxy.entity_exists(mapped_input):
		return None

	return mapped_input.json


def get_current_stamp() -> int:
	dt = datetime.datetime.now(timezone.utc)

	utc_time = dt.replace(tzinfo=timezone.utc)
	utc_timestamp = utc_time.timestamp()
	return int(utc_timestamp)


def ensure_time_to_respond(hour_delay: int, timestamp: int) -> bool:
	hours_since_post = (get_current_stamp() - timestamp) / 60 / 60
	logging.debug(f":: Hour Delay {hour_delay} Time Since: {hours_since_post}")
	return hour_delay > hours_since_post
