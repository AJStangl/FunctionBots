import datetime
import json
import logging
import os

import azure.functions as func
from praw import Reddit
from praw.models import Submission
from praw.models.reddit.base import RedditBase
from praw.reddit import Comment

from shared_code.queue_utility.service_proxy import QueueServiceProxy


def main(commentTimer: func.TimerRequest) -> None:

	bot_name = os.environ["Bot"]

	reddit = get_praw_instance(bot_name)

	user = reddit.user.me()

	logging.info(f":: Polling For Comments for User {user.name}")

	subs = get_subs_from_configuration()
	logging.info(f":: Obtaining New/Incoming Submissions For Subreddit {subs}")

	queue_service = QueueServiceProxy()

	subreddit = reddit.subreddit(subs)

	logging.info(f":: Subreddit {subreddit} connected. Obtaining Stream...")

	comments = subreddit.stream.comments()

	for comment in comments:
		if comment is None:
			break

		result = process_to_model(comment, user.name)
		result = queue_service.put_message("stream-input-comment-queue", convert_to_message(result))
		logging.info(f":: Comment {result.id} Sent To Queue for Comment {comment.id}")


def get_praw_instance(bot_name: str) -> Reddit:
	logging.info(f":: Initializing Reddit Praw Instance")
	reddit = Reddit(site_name=bot_name)
	return reddit


def get_subs_from_configuration() -> str:
	subs = "+".join("CoopAndPabloPlayhouse,SubSimGPT2Interactive".split(","))
	return subs


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
