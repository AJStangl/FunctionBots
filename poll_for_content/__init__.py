import datetime
import logging
import typing
from typing import Optional

import azure.functions as func
from praw.models.reddit.base import RedditBase
from praw.reddit import Redditor

from shared_code.helpers.reddit_helper import RedditHelper
from shared_code.storage_proxies.table_proxy import TableServiceProxy

def main(contentTimer: func.TimerRequest, msg: func.Out[typing.List[str]]) -> None:

	helper = RedditHelper()

	logging.info(f":: Poll For Submission trigger called at {datetime.date.today()}")

	proxy = TableServiceProxy()

	bot_name = helper.get_bot_name()

	reddit = helper.get_praw_instance(bot_name)

	user = reddit.user.me()

	logging.info(f":: Polling For Submissions for User: {user.name}")

	subs = helper.get_subs_from_configuration()

	logging.info(f":: Obtaining New/Incoming Streams For Subreddit: {subs}")

	subreddit = reddit.subreddit(subs)

	logging.info(f":: Subreddit {subreddit} connected. Obtaining Stream...")

	messages = []

	logging.info(f":: Processing Stream For submissions")
	submissions = subreddit.stream.submissions(pause_after=0)
	for submission in submissions:
		if submission is None:
			break
		m = process_thing(submission, user, "Submission", proxy, helper)
		if m is not None:
			messages.append(m)

	logging.info(f":: Processing Stream For comments")
	comments = subreddit.stream.comments(pause_after=0)

	for comment in comments:
		if comment is None:
			break
		m = process_thing(comment, user, "Comment", proxy, helper)
		if m is not None:
			messages.append(m)

	if len(messages) > 0:
		msg.set(messages)
		logging.info(":: Sent Message Batch Successfully")
		return

	msg.set([])
	logging.info(f":: Process Complete, no new inputs from stream")
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

