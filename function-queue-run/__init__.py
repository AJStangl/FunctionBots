import datetime
import json
import logging
import os
import random
from typing import Optional
import time
import azure.functions as func
from azure.storage.queue import TextBase64EncodePolicy
from praw.models import Submission
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


def main(message: func.QueueMessage) -> None:
	all_workers = ["worker-1", "worker-2", "worker-3"]

	reddit_helper: RedditManager = RedditManager()

	repository: DataRepository = DataRepository()

	queue_proxy: QueueServiceProxy = QueueServiceProxy()

	bot_configuration_manager: BotConfigurationManager = BotConfigurationManager()

	bot_name_list = [bot.Name.upper() for bot in bot_configuration_manager.get_configuration()]

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

	logging.info(f":: Initializing Reply Before Main Routine for {bot_name}")

	reply_service.invoke()

	####################################################################################################################
	logging.info(f":: Handling pending comments and submissions from database for {bot_name}")

	logging.info(f":: Fetching latest Comments For {bot_name}")
	pending_comments = repository.search_for_pending("Comment", bot_name)

	logging.info(f":: Fetching latest Submissions For {bot_name}")
	pending_submissions = repository.search_for_pending("Submission", bot_name)

	for record in chain_listing_generators(pending_comments, pending_submissions):
		if record is None:
			logging.info(f":: No records found for comments or submission to process for {bot_name}")
			continue

		# Extract the record and set the status
		record = record['TableRecord']
		record.Status = 1
		processed = process_input(record, reddit, tagging_mixin)
		if processed is None:
			logging.info(f":: Failed To Process {record.RedditId} for {record.RespondingBot}")
			continue

		record.TextGenerationPrompt = processed

		message_live_in_hours = 60 * 60 * 4

		reply_probability_target = 60

		if record.InputType == "Submission":
			repository.update_entity(record)
			queue = queue_proxy.service.get_queue_client(random.choice(all_workers), message_encode_policy=TextBase64EncodePolicy())
			queue.send_message(json.dumps(record.as_dict()), time_to_live=message_live_in_hours)
			logging.info(f":: Sending {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation")
			continue

		if record.ReplyProbability > reply_probability_target and record.InputType == "Comment":
			queue = queue_proxy.service.get_queue_client(random.choice(all_workers), message_encode_policy=TextBase64EncodePolicy())
			queue.send_message(json.dumps(record.as_dict()), time_to_live=message_live_in_hours)
			repository.update_entity(record)
			logging.info(f":: Sending {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation")
			continue

		else:
			logging.info(f":: Ignoring {record.InputType} for {record.RespondingBot} has a Probability of {record.ReplyProbability} but needs {reply_probability_target}")
			record.Status = 2
			repository.update_entity(record)
			continue

	####################################################################################################################

	logging.info(f":: Collecting Submissions for {bot_name}")
	submissions: [Submission] = subreddit.stream.submissions(pause_after=0, skip_existing=False)

	logging.info(f":: Collecting Comments for {bot_name}")
	comments: [Comment] = subreddit.stream.comments(pause_after=0, skip_existing=False)

	logging.info(f":: Handling Submissions for {bot_name}")
	start_time: float = time.time()
	max_search_time = 120
	for reddit_thing in submissions:
		if reddit_thing is None:
			break
		if round(time.time() - start_time) > max_search_time:
			logging.info(f":: Halting Collection Past {max_search_time} seconds For Submissions")
			break
		handle_submission(reddit_thing, user, repository, reply_logic)

	start_time = time.time()
	logging.info(f":: Handling Incoming Comments for {bot_name}")
	for reddit_thing in comments:
		if reddit_thing is None:
			break
		if round(time.time() - start_time) > max_search_time:
			logging.info(f":: Halting Collection Past {max_search_time} seconds For Comments")
			break
		handle_comment(reddit_thing, user, repository, reply_logic, reddit)
	####################################################################################################################

	logging.info(f":: Initializing Reply After Main Routine for {bot_name}")
	reply_service.invoke()

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
		if thing is None:
			return None
		history = tagging_mixin.collate_tagged_comment_history(thing)
		cleaned_history = tagging_mixin.remove_username_mentions_from_string(history, record.RespondingBot)
		reply_start_tag = tagging_mixin.get_reply_tag(thing, record.RespondingBot)
		prompt = cleaned_history + reply_start_tag
		return prompt


def handle_submission(thing: Submission, user: Redditor, repository: DataRepository, reply_probability: ReplyLogic) -> Optional[TableRecord]:

	# Ignore when submission is the same for the submitter and responder
	if user.name == getattr(thing.author, 'name', ''):
		return None

	if timestamp_to_hours(thing.created_utc) > 16:
		logging.debug(f":: Submission to old {thing.id} for {user.name}")
		return None

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

	entity = repository.create_if_not_exist(mapped_input)

	return entity


def handle_comment(comment: Comment, user: Redditor, repository: DataRepository, reply_probability: ReplyLogic, instance: Reddit) -> Optional[TableRecord]:

	probability = reply_probability.calculate_reply_probability(comment)

	if probability == 0:
		logging.info(f":: Reply Probability for {comment.id} is 0 - {user.name}")
		return None

	mapped_input: TableRecord = TableHelper.map_base_to_message(
		reddit_id=comment.id,
		sub_reddit=comment.subreddit.display_name,
		input_type="Comment",
		submitted_date=comment.submission.created,
		author=getattr(comment.author, 'name', ''),
		responding_bot=user.name,
		time_in_hours=timestamp_to_hours(comment.created),
		reply_probability=probability,
		url=comment.permalink)

	entity = repository.create_if_not_exist(mapped_input)

	return entity


def timestamp_to_hours(utc_timestamp):
	return int((datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(utc_timestamp)).total_seconds() / 3600) - 4


def chain_listing_generators(*iterables):
	# Special tool for chaining PRAW's listing generators
	# It joins the three iterables together so that we can DRY
	for it in iterables:
		for element in it:
			if element is None:
				break
			else:
				yield element