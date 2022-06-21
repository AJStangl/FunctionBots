import json
import logging
import random
from datetime import datetime
from typing import Optional

import azure.functions as func
from praw.models import Submission

from shared_code.database.repository import DataRepository, TableRecord
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.helpers.tagging import TaggingMixin
from shared_code.models.bot_configuration import BotConfigurationManager
from shared_code.storage_proxies.service_proxy import QueueServiceProxy


def main(message: func.QueueMessage) -> None:
	bot_config = json.loads(message.get_body().decode('utf-8'))

	bot_name = bot_config["Name"]

	logging.info(f":: Starting Table Collection For {bot_name}")

	repository: DataRepository = DataRepository()

	queue_proxy: QueueServiceProxy = QueueServiceProxy()

	helper: RedditManager = RedditManager()

	bot_config_manager = BotConfigurationManager()

	submission_workers = ["worker-1"]

	comment_workers = ["worker-2", "worker-3"]

	bots = [item.Name for item in bot_config_manager.configurations]

	bot = random.choice(bots)

	pending_comments = repository.search_for_pending("Comment", bot_name)

	for entity in pending_comments:
		if entity is None:
			continue
		record = entity['TableRecord']
		record.Status = 1
		processed = process_input(helper, record)
		record.TextGenerationPrompt = processed
		if bot_config_manager.get_configuration_by_name(record.Author) is None:
			queue = queue_proxy.service.get_queue_client(random.choice(submission_workers))
			queue.send_message(json.dumps(record.as_dict()))
			repository.update_entity(record)
			continue

		choice = random.randint(1, 100)
		if choice > 30:
			queue = queue_proxy.service.get_queue_client(random.choice(comment_workers))
			queue.send_message(json.dumps(record.as_dict()))
			repository.update_entity(record)
			continue
		else:
			record.Status = 2
			repository.update_entity(record)
			continue

	pending_submissions = repository.search_for_pending("Submission", bot)

	for entity in pending_submissions:
		if entity is None:
			continue
		record = entity['TableRecord']
		record.Status = 1
		processed = process_input(helper, record)
		record.TextGenerationPrompt = processed
		repository.update_entity(record)
		queue = queue_proxy.service.get_queue_client(random.choice(submission_workers))
		queue.send_message(json.dumps(record.as_dict()))




def process_input(helper: RedditManager, record: TableRecord) -> Optional[str]:
	tagging_mixin = TaggingMixin()
	instance = helper.get_praw_instance_for_bot(record.RespondingBot)

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


def timestamp_to_hours(utc_timestamp):
	return (datetime.utcnow() - datetime.fromtimestamp(utc_timestamp)).total_seconds() / 3600
