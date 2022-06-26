import datetime
import json
import logging
import os
import random
from typing import Optional

import azure.functions as func
from azure.storage.queue import TextBase64EncodePolicy
from praw.models import Submission
from praw.models.reddit.base import RedditBase
from praw.reddit import Redditor, Reddit, Comment

from shared_code.database.instance import TableRecord
from shared_code.database.repository import DataRepository
from shared_code.helpers.record_helper import TableHelper
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.helpers.reply_logic import ReplyLogic
from shared_code.helpers.tagging import TaggingMixin
from shared_code.models.bot_configuration import BotConfiguration, BotConfigurationManager
from shared_code.services.reply_service import ReplyService
from shared_code.storage_proxies.service_proxy import QueueServiceProxy

"""
Main Function For Bot

Input: poll-queue
"""


def main(message: func.QueueMessage) -> None:
	submission_workers = ["worker-1"]

	comment_workers = ["worker-2", "worker-3"]

	all_workers = ["worker-1", "worker-2", "worker-3"]

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

	reply_service: ReplyService = ReplyService()

	reply_logic: ReplyLogic = ReplyLogic(reddit)

	user = reddit.user.me()

	subs = reddit_helper.get_subs_from_configuration(bot_name)

	subreddit = reddit.subreddit(subs)

	logging.info(f":: Initializing Reply Before Main Routine")
	reply_service.invoke()

	####################################################################################################################
	logging.info(f":: Handling pending comments and submissions from database for {bot_name}")
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

		reply_probability_target = random.randint(1, 100)

		if record.InputType == "Submission":
			repository.update_entity(record)
			queue = queue_proxy.service.get_queue_client(random.choice(all_workers), message_encode_policy=TextBase64EncodePolicy())
			queue.send_message(json.dumps(record.as_dict()))
			logging.debug(f":: Sending {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation")
			continue

		if record.ReplyProbability > reply_probability_target and record.InputType == "Comment":
			queue = queue_proxy.service.get_queue_client(random.choice(all_workers), message_encode_policy=TextBase64EncodePolicy())
			queue.send_message(json.dumps(record.as_dict()))
			repository.update_entity(record)
			logging.debug(f":: Sending {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation")
			continue

		else:
			logging.debug(f":: Ignoring {record.InputType} for {record.RespondingBot} has a Probability of {record.ReplyProbability} but needs {reply_probability_target}")
			record.Status = 2
			repository.update_entity(record)
			continue

	####################################################################################################################
	logging.info(f":: Initializing Reply After Main Routine")
	reply_service.invoke()

	logging.info(f":: Collecting Submissions for {bot_name}")
	submissions: [Submission] = subreddit.stream.submissions(pause_after=0, skip_existing=False)

	logging.info(f":: Collecting Comments for {bot_name}")
	comments: [Comment] = subreddit.stream.comments(pause_after=0, skip_existing=False)

	new_inputs = []
	for reddit_thing in submissions:
		if reddit_thing is None:
			break
		handled = handle_submission(reddit_thing, user, repository, reply_logic)
		if handled is not None:
			new_inputs.append(handled)

	for reddit_thing in comments:
		if reddit_thing is None:
			break
		handled = handle_comment(reddit_thing, user, repository, reddit_helper, reply_logic)
		if handled is not None:
			new_inputs.append(handled)

	####################################################################################################################
	logging.info(f":: Polling Method Complete For {bot_name}")
	return None


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


def handle_submission(thing: Submission, user: Redditor, repository: DataRepository, reply_probability: ReplyLogic) -> Optional[TableRecord]:
	probability = reply_probability.calculate_reply_probability(thing)
	mapped_input: TableRecord = TableHelper.map_base_to_message(
		reddit_id=thing.id,
		sub_reddit=thing.subreddit.display_name,
		input_type="Submission",
		time_in_hours=timestamp_to_hours(thing.created),
		submitted_date=thing.created,
		author=getattr(thing.author, 'name', ''),
		responding_bot=user.name,
		reply_probability=probability,
		url=thing.url
	)

	# Filter Out Where responding bot is the author
	if mapped_input.RespondingBot == mapped_input.Author:
		return None

	if timestamp_to_hours(thing.created_utc) > 12:
		logging.debug(f":: {mapped_input.InputType} to old {mapped_input.Id} for {user.name}")
		return None

	entity = repository.create_if_not_exist(mapped_input)

	return entity


def handle_comment(comment: Comment, user: Redditor, repository: DataRepository, helper: RedditManager, reply_probability: ReplyLogic) -> Optional[TableRecord]:
	probability = reply_probability.calculate_reply_probability(comment)
	mapped_input: TableRecord = TableHelper.map_base_to_message(
		reddit_id=comment.id,
		sub_reddit=comment.subreddit.display_name,
		input_type="Comment",
		submitted_date=comment.created,
		author=getattr(comment.author, 'name', ''),
		responding_bot=user.name,
		time_in_hours=timestamp_to_hours(comment.created),
		reply_probability=probability,
		url=comment.permalink,
	)

	if mapped_input.RespondingBot == mapped_input.Author:
		return None

	sub_id = comment.submission.id

	instance = helper.get_praw_instance_for_bot(user.name)

	sub = instance.submission(id=sub_id)

	if sub.num_comments > int(os.environ["MaxComments"]):
		logging.debug(f":: Submission for Comment Has To Many Replies {comment.submission.num_comments} for {user.name}")
		return None

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
