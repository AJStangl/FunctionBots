import datetime
import json
import logging
import typing
import azure.functions as func
from praw.models.reddit.base import RedditBase
from praw.reddit import Redditor

from shared_code.helpers.reddit_helper import RedditHelper
from shared_code.queue_utility.service_proxy import QueueServiceProxy


def main(contentTimer: func.TimerRequest, msg: func.Out[typing.List[str]]) -> None:
	logging.info(f":: Poll For Submission trigger called at {datetime.date.today()}")

	bot_name = RedditHelper.get_bot_name()

	reddit = RedditHelper.get_praw_instance(bot_name)

	user = reddit.user.me()

	logging.info(f":: Polling For Submissions for User: {user.name}")

	subs = RedditHelper.get_subs_from_configuration()

	logging.info(f":: Obtaining New/Incoming Submissions For Subreddit: {subs}")

	# queue_service = QueueServiceProxy()

	subreddit = reddit.subreddit(subs)

	logging.info(f":: Subreddit {subreddit} connected. Obtaining Stream...")

	submissions = subreddit.stream.submissions(pause_after=0)

	messages = []

	logging.info(f":: Processing Stream For submissions")
	for submission in submissions:
		if submission is None:
			break
		m = process_thing(submission, user, "Submission")
		messages.append(m)

	comments = subreddit.stream.comments(pause_after=0)

	for comment in comments:
		if comment is None:
			break
		m = process_thing(comment, user, "Comment")
		messages.append(m)

	msg.set(messages)
	logging.info(":: Sent Message Batch Successfully")
	logging.info(f":: Process Complete")

	return


def process_thing(submission: RedditBase, user: Redditor, input_type: str) -> str:
	mapped_submission = RedditHelper.map_base_to_message(submission, user.name, input_type)
	return mapped_submission.to_json()

