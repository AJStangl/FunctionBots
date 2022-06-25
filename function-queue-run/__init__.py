import json
import logging
import os
import typing
from typing import Optional
import random
import azure.functions as func
from azure.storage.queue import TextBase64EncodePolicy
from praw.models import Submission
from praw.models.reddit.base import RedditBase
from praw.reddit import Redditor, Reddit, Comment

from shared_code.helpers.reddit_helper import RedditManager
from shared_code.database.repository import DataRepository
from shared_code.database.instance import TableRecord
from shared_code.helpers.reply_logic import ReplyLogic
from shared_code.helpers.record_helper import TableHelper
from shared_code.helpers.tagging import TaggingMixin
from shared_code.models.bot_configuration import BotConfiguration, BotConfigurationManager
import datetime

from shared_code.services.reply_service import ReplyService
from shared_code.storage_proxies.service_proxy import QueueServiceProxy

"""
Main Function For Bot

Input: poll-queue
"""
def main(message: func.QueueMessage) -> None:

	submission_workers = ["worker-1"]

	comment_workers = ["worker-2", "worker-3"]

	reddit_helper: RedditManager = RedditManager()

	repository: DataRepository = DataRepository()

	queue_proxy: QueueServiceProxy = QueueServiceProxy()

	bot_config_manager = BotConfigurationManager()

	tagging_mixin: TaggingMixin = TaggingMixin()

	message_json = message.get_body().decode('utf-8')

	incoming_message: BotConfiguration = json.loads(message_json, object_hook=lambda d: BotConfiguration(**d))

	bot_name = incoming_message.Name

	logging.info(f":: Starting Main Routine For {bot_name}")

	reddit = reddit_helper.get_praw_instance_for_bot(bot_name)

	reply_service: ReplyService = ReplyService(reddit)

	reply_logic: ReplyLogic = ReplyLogic(reddit)

	reply_service.invoke()

	user = reddit.user.me()

	subs = reddit_helper.get_subs_from_configuration(bot_name)

	subreddit = reddit.subreddit(subs)

	submissions: [Submission] = subreddit.stream.submissions(pause_after=0, skip_existing=False)

	comments: [Comment] = subreddit.stream.comments(pause_after=0, skip_existing=False)

	# loop_interval = get_loop_interval(120)

	new_inputs = []
	logging.info(f":: Starting poll for submissions and comments")
	for reddit_thing in chain_listing_generators(submissions, comments):
		handled = handle(reddit_thing, user, repository, reddit_helper, reply_logic)
		new_inputs.append(handled)
		# if check_loop_interval(loop_interval):
		# 	break

	logging.info(f":: Polling Complete. {len(new_inputs)} have been found - Starting Processing")

	pending_comments = repository.search_for_pending("Comment", bot_name)

	pending_submissions = repository.search_for_pending("Submission", bot_name)

	for record in chain_listing_generators(pending_comments, pending_submissions):
		if record is None:
			continue

		# Extract the record and set the status
		record = record['TableRecord']
		record.Status = 1
		processed = process_input(record, reddit, tagging_mixin)
		record.TextGenerationPrompt = processed

		if record.InputType == "Submission":
			repository.update_entity(record)
			queue = queue_proxy.service.get_queue_client(random.choice(submission_workers), message_encode_policy=TextBase64EncodePolicy())
			queue.send_message(json.dumps(record.as_dict()), time_to_live=60*60*8)
			logging.info(f":: Sending {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation")

		if record.InputType == "Comment":
			if bot_config_manager.get_configuration_by_name(record.Author) is None:
				queue = queue_proxy.service.get_queue_client(random.choice(submission_workers), message_encode_policy=TextBase64EncodePolicy())
				queue.send_message(json.dumps(record.as_dict()), time_to_live=60*60*8)
				repository.update_entity(record)
				logging.info(f":: Sending Priority {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation")
				continue

			if record.ReplyProbability > 60:
				queue = queue_proxy.service.get_queue_client(random.choice(comment_workers), message_encode_policy=TextBase64EncodePolicy())
				queue.send_message(json.dumps(record.as_dict()), time_to_live=60*60*8)
				repository.update_entity(record)
				logging.info(f":: Sending {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation")
				continue
			else:
				record.Status = 2
				repository.update_entity(record)
				continue

def get_loop_interval(seconds: int) -> datetime:
	return datetime.datetime.now() + datetime.timedelta(seconds=seconds)


def check_loop_interval(loop_interval: datetime) -> bool:
	return datetime.datetime.now() > loop_interval


def process_input(record: TableRecord, instance: Reddit, tagging_mixin: TaggingMixin) -> Optional[str]:
	if record.InputType == "Submission":
		thing: Submission = instance.submission(id=record.RedditId)
		history = tagging_mixin.collate_tagged_comment_history(thing)
		cleaned_history = tagging_mixin.remove_username_mentions_from_string(history, record.RespondingBot)
		reply_start_tag = tagging_mixin.get_reply_tag(thing, record.RespondingBot)
		prompt = cleaned_history + reply_start_tag
		return prompt

	if record.InputType == "Comment":
		thing = instance.comment(id=record.RedditId)
		history = tagging_mixin.collate_tagged_comment_history(thing)
		cleaned_history = tagging_mixin.remove_username_mentions_from_string(history, record.RespondingBot)
		reply_start_tag = tagging_mixin.get_reply_tag(thing, record.RespondingBot)
		prompt = cleaned_history + reply_start_tag
		return prompt


def handle(thing: RedditBase, user: Redditor, repository: DataRepository, helper: RedditManager, reply_probability: ReplyLogic) -> Optional[TableRecord]:
	if isinstance(thing, Submission):
		handled_submission = handle_submission(thing, user, repository, reply_probability)
		return handled_submission
	if isinstance(thing, Comment):
		handled_comment = handle_comment(thing, user, repository, helper, reply_probability)
		return handled_comment


def handle_submission(thing: Submission, user: Redditor, repository: DataRepository, reply_probability: ReplyLogic) -> Optional[TableRecord]:
	# thing, user.name, "Submission"
	probability = reply_probability.calculate_reply_probability(thing)
	mapped_input: TableRecord = TableHelper.map_base_to_message(
		reddit_id=thing.id,
		sub_reddit=thing.subreddit.display_name,
		input_type="Submission",
		time_in_hours=timestamp_to_hours(thing.created),
		submitted_date=thing.created,
		author=getattr(thing.author, 'name', ''),
		responding_bot=user.name,
		reply_probability=probability
	)

	# Filter Out Where responding bot is the author
	if mapped_input.RespondingBot == mapped_input.Author:
		return None

	if timestamp_to_hours(thing.created_utc) > 12:
		logging.debug(f":: {mapped_input.InputType} to old {mapped_input.Id} for {user.name}")
		return None

	entity = repository.create_if_not_exist(mapped_input)

	return entity


def handle_comment(comment: Comment, user: Redditor, repository: DataRepository, helper: RedditManager, reply_probability: ReplyLogic) -> Optional[
	TableRecord]:
	probability = reply_probability.calculate_reply_probability(comment)
	mapped_input: TableRecord = TableHelper.map_base_to_message(
		reddit_id=comment.id,
		sub_reddit=comment.subreddit.display_name,
		input_type="Comment",
		submitted_date=comment.created,
		author=getattr(comment.author, 'name', ''),
		responding_bot=user.name,
		time_in_hours=timestamp_to_hours(comment.created),
		reply_probability=probability
	)

	if mapped_input.RespondingBot == mapped_input.Author:
		return None

	sub_id = comment.submission.id

	instance = helper.get_praw_instance_for_bot(user.name)

	sub = instance.submission(id=sub_id)

	if sub.num_comments > int(os.environ["MaxComments"]):
		logging.debug(f":: Submission for Comment Has To Many Replies {comment.submission.num_comments} for {user.name}")
		return None

	# comment_created_hours = timestamp_to_hours(comment.created_utc)

	# submission_created_hours = timestamp_to_hours(sub.created_utc)

	# delta = abs(comment_created_hours - submission_created_hours)

	# max_comment_submission_diff = int(os.environ["MaxCommentSubmissionTimeDifference"])

	# if delta > int(os.environ["MaxCommentSubmissionTimeDifference"]):
	# 	logging.debug(
	# 		f":: Time between comment and reply is {delta} > {max_comment_submission_diff} hours for {user.name}|{comment.id}")
	# 	return None

	if comment.submission.locked:
		logging.debug(f":: Comment is locked! Skipping...")
		return None
	else:
		entity = repository.create_if_not_exist(mapped_input)
		return entity


def timestamp_to_hours(utc_timestamp):
	return int((datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(utc_timestamp)).total_seconds() / 3600)


def chain_listing_generators(*iterables):
	# Special tool for chaining PRAW's listing generators
	# It joins the three iterables together so that we can DRY
	for it in iterables:
		for element in it:
			if element is None:
				break
			else:
				yield element
