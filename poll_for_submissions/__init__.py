import datetime
import json
import logging
import os

import azure.functions as func
from praw import Reddit
from praw.models import Submission
from praw.models.reddit.base import RedditBase

from shared_code.queue_utility.service_proxy import QueueServiceProxy


def main(submissionTimer: func.TimerRequest) -> None:
	logging.info(f":: Poll For Submission trigger called at {datetime.date.today()}")

	bot_name = os.environ["Bot"]
	reddit = get_praw_instance(bot_name)

	user = reddit.user.me()
	logging.info(f":: Polling For Submissions for User {user.name}")

	subs = get_subs_from_configuration()
	logging.info(f":: Obtaining New/Incoming Submissions For Subreddit {subs}")

	queue_service = QueueServiceProxy()

	subreddit = reddit.subreddit(subs)

	logging.info(f":: Subreddit {subreddit} connected. Obtaining Stream...")

	submissions = subreddit.stream.submissions()

	for submission in submissions:
		if submission is None:
			break

		result = process_to_model(submission, user.name)
		result = queue_service.put_message("stream-input-submission-queue", convert_to_message(result))
		logging.info(f":: Submission {result.id} Sent To Queue for Submission {submission.id}")


def get_praw_instance(bot_name: str) -> Reddit:
	logging.info(f":: Initializing Reddit Praw Instance")
	reddit = Reddit(site_name=bot_name)
	return reddit


def get_subs_from_configuration() -> str:
	subs = "+".join(os.environ["SubReddit"].split(","))
	return subs


def process_to_model(submission: RedditBase, bot_username: str) -> dict:

	record_dict = {
		'source_name': submission.name,
		'created_utc': submission.created_utc,
		'author': getattr(submission.author, 'name', ''),
		'subreddit': submission.subreddit.display_name,
		'bot_username': bot_username
	}
	return record_dict


def convert_to_message(input_dict: dict) -> str:
	return json.dumps(input_dict)


