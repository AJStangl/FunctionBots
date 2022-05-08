import datetime
import logging
import asyncpraw
import os
import azure.functions as func
from asyncpraw import Reddit


async def main(mytimer: func.TimerRequest) -> None:
	utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()

	# TODO: In order to support multiple bots we will need to change what is below into a loop
	logging.info(f":: Poll For Submission trigger called at {utc_timestamp}")

	reddit = get_praw_instance("LarissaBot-GPT2")

	user = await reddit.user.me()

	logging.info(f":: Polling For Submissions for User {user.name}")

	subs = get_subs_from_configuration()
	print(subs)

	await reddit.close()


def get_praw_instance(bot_name: str) -> Reddit:
	logging.info(f":: Initializing Reddit Praw Instance")
	reddit = asyncpraw.Reddit(site_name=bot_name)
	return reddit


def get_recent_submissions(subreddit_name: str):
	logging.info(f":: Obtaining New/Incoming Submissions For Subreddit {subreddit_name}")


def get_subs_from_configuration() -> [str]:
	subs = os.environ["SubReddit"].split(",")
	return subs
