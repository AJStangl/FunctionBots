import datetime
import logging

import azure.functions as func
from praw import Reddit
from praw.models import Submission
from praw.reddit import Comment


def main(mytimer: func.TimerRequest) -> None:
	logging.info(f":: Poll For Submission trigger called at {datetime.date.today()}")

	reddit = get_praw_instance("LarissaBot-GPT2")

	user = reddit.user.me()

	logging.info(f":: Polling For Submissions for User {user.name}")

	subs = get_subs_from_configuration()

	logging.info(f":: Obtaining New/Incoming Submissions For Subreddit {subs}")

	subreddit = reddit.subreddit(subs)

	logging.info(f":: Subreddit {subreddit} connected. Obtaining Stream...")

	submissions = subreddit.stream.submissions(pause_after=0)
	comments = subreddit.stream.comments(pause_after=0)

	for submission in submissions:
		if submission is None:
			break
		result = process_submission_to_model(submission, user.name)
		print(result)

	for comment in comments:
		if comment is None:
			break
		result = process_comment_to_model(comment, user.name)
		print(result)


def get_praw_instance(bot_name: str) -> Reddit:
	logging.info(f":: Initializing Reddit Praw Instance")
	reddit = Reddit(site_name=bot_name)
	return reddit


def get_subs_from_configuration() -> str:
	subs = "+".join("CoopAndPabloPlayhouse,SubSimGPT2Interactive".split(","))
	return subs


def process_submission_to_model(submission: Submission, bot_username: str) -> dict:
	record_dict = {
		'source_name': submission.name,
		'created_utc': submission.created_utc,
		'author': getattr(submission.author, 'name', ''),
		'subreddit': submission.subreddit.display_name,
		'bot_username': bot_username
	}
	return record_dict


def process_comment_to_model(comment: Comment, bot_username: str) -> dict:
	record_dict = {
		'source_name': comment.name,
		'created_utc': comment.created_utc,
		'author': getattr(comment.author, 'name', ''),
		'subreddit': comment.subreddit.display_name,
		'bot_username': bot_username
	}
	return record_dict


