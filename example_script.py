import base64
import datetime
import json
import logging
from operator import attrgetter
from typing import Optional

from azure.core.paging import ItemPaged
from azure.data.tables import TableClient, TableEntity, TableServiceClient
from azure.storage.queue import QueueServiceClient, QueueClient, QueueMessage
from praw import Reddit
from praw.models import Submission, Comment, Subreddit
from praw.models.reddit.base import RedditBase
from praw.models.reddit.redditor import RedditorStream

from shared_code.generators.text.model_text_generator import ModelTextGenerator
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.helpers.tagging import TaggingMixin
from shared_code.storage_proxies.service_proxy import QueueServiceProxy
from shared_code.storage_proxies.table_proxy import TableServiceProxy, TableRecord


def run_submission_collection():
	proxy: TableServiceProxy = TableServiceProxy()

	queue_proxy: QueueServiceProxy = QueueServiceProxy()

	helper: RedditManager = RedditManager()

	client: TableClient = proxy.get_client()

	queue = queue_proxy.service.get_queue_client("prompt-queue")

	query_string = "has_responded eq false and input_type eq 'Submission' and text_generation_prompt eq ''"

	pending_submissions: ItemPaged[TableEntity] = client.query_entities(query_string, results_per_page=10)
	submission_results = []

	for pages in pending_submissions.by_page():
		for page in pages:
			record: TableRecord = json.loads(json.dumps(page), object_hook=lambda d: TableRecord(**d))
			submission_results.append(record)
		break

	sorted_submission_results = sorted(submission_results, key=lambda x: x.content_date_submitted_utc, reverse=True)

	for record in sorted_submission_results:
		processed = process_input(helper, record)
		record.text_generation_prompt = processed

		queue.send_message(record.json)

	comment_results = []
	query_string = "has_responded eq false and input_type eq 'Comment' and text_generation_prompt eq ''"
	pending_comments : ItemPaged[TableEntity] = client.query_entities(query_string, results_per_page=100)

	for pages in pending_comments.by_page():
		for page in pages:
			record: TableRecord = json.loads(json.dumps(page), object_hook=lambda d: TableRecord(**d))
			comment_results.append(record)
		break

	sorted_comment_results = sorted(submission_results, key=lambda x: x.content_date_submitted_utc, reverse=True)

	for record in sorted_comment_results:
		processed = process_input(helper, record)
		record.text_generation_prompt = processed

		queue.send_message(record.json)


def process_input(helper: RedditManager, incoming_message: TableRecord) -> Optional[str]:
	tagging_mixin = TaggingMixin()
	instance = helper.get_praw_instance_for_bot(incoming_message.responding_bot)

	if incoming_message.input_type == "Submission":
		thing: Submission = instance.submission(id=incoming_message.id)
		history = tagging_mixin.collate_tagged_comment_history(thing)
		cleaned_history = tagging_mixin.remove_username_mentions_from_string(history, incoming_message.responding_bot)
		reply_start_tag = tagging_mixin.get_reply_tag(thing, incoming_message.responding_bot)
		prompt = cleaned_history + reply_start_tag
		return prompt

	if incoming_message.input_type == "Comment":
		thing = instance.comment(id=incoming_message.id)
		history = tagging_mixin.collate_tagged_comment_history(thing)
		cleaned_history = tagging_mixin.remove_username_mentions_from_string(history, incoming_message.responding_bot)
		reply_start_tag = tagging_mixin.get_reply_tag(thing, incoming_message.responding_bot)
		prompt = cleaned_history + reply_start_tag
		return prompt


def run_reply() -> None:
	tagging: TaggingMixin = TaggingMixin()
	queue_service: QueueServiceClient = QueueServiceProxy().service
	table_service: TableServiceClient = TableServiceProxy().service
	helper: RedditManager = RedditManager()

	queue_client: QueueClient = queue_service.get_queue_client("reply-queue")

	table_client: TableClient = table_service.get_table_client("tracking")

	if len(queue_client.peek_messages()) == 0:
		return

	message: QueueMessage = queue_client.receive_message()
	queue_client.delete_message(message)
	queue_client.close()

	record: TableRecord = handle_incoming_message(message)

	prompt: str = record.text_generation_prompt

	response: str = record.text_generation_response

	extract: dict = tagging.extract_reply_from_generated_text(prompt, response)

	reddit: Reddit = helper.get_praw_instance_for_bot(bot_name=record.responding_bot)

	entity: TableEntity = table_client.get_entity(record.PartitionKey, record.RowKey)

	if record.input_type == "Submission":
		sub_instance: Submission = reddit.submission(id=record.id)
		sub_instance.reply(extract)
		entity["has_responded"] = True
		table_client.update_entity(entity)

	if record.input_type == "Comment":
		comment_instance: Comment = reddit.comment(id=record.id)
		comment_instance.reply(extract)
		entity["has_responded"] = True
		table_client.update_entity(entity)

	table_client.close()

def run_text_generation() -> None:
	logging.debug(f":: Text Generation Timer Trigger Called")

	queue_service: QueueServiceClient = QueueServiceProxy().service
	table_service: TableServiceClient = TableServiceProxy().service

	queue_client: QueueClient = queue_service.get_queue_client("prompt-queue")
	table_client: TableClient = table_service.get_table_client("tracking")

	if len(queue_client.peek_messages()) == 0:
		logging.debug(":: No New Messages")
		return

	message = queue_client.receive_message()

	queue_client.delete_message(message)

	queue_client.close()

	incoming_message: TableRecord = handle_incoming_message(message)

	bot_name = incoming_message.responding_bot

	prompt = incoming_message.text_generation_prompt

	logging.debug(f":: Trigger For Model Generation called at {datetime.datetime.now()} for {bot_name}")

	model_generator = ModelTextGenerator()

	result = model_generator.generate_text(bot_name, prompt)

	entity = table_client.get_entity(partition_key=incoming_message.PartitionKey, row_key=incoming_message.RowKey)

	entity["text_generation_prompt"] = prompt

	entity["text_generation_response"] = result

	table_client.update_entity(entity)


def handle_incoming_message(message) -> TableRecord:
	try:
		incoming_message: TableRecord = json.loads(base64.b64decode(message.content), object_hook=lambda d: TableRecord(**d))
		return incoming_message
	except Exception:
		incoming_message: TableRecord = json.loads(message.content, object_hook=lambda d: TableRecord(**d))
		return incoming_message


def do_thing():
	queue_service: QueueServiceClient = QueueServiceProxy().service
	queue_client: QueueClient = queue_service.get_queue_client("prompt-queue")
	message = queue_client.receive_message()
	foo: TableRecord = handle_incoming_message(message)
	bar = (foo.content_date_submitted_utc / 60) / 60

def foo():
	proxy = QueueServiceProxy()
	service = proxy.service
	queue_client = service.get_queue_client("prompt-queue")
	peek = queue_client.peek_messages()

def get_sub_and_comment_forest():
	reddit = RedditManager().get_praw_instance_for_bot(bot_name="CoopBot-GPT2")

	sub: Subreddit = reddit.subreddit("CoopAndPabloPlayHouse")
	stream = sub.stream.submissions(pause_after=0)

	submissions: [Submission] = []
	comments: [Comment] = []

	for submission in stream:
		if submission is None:
			break
		submissions.append(submission)

	mapped_results = []
	for item in submissions:
		if filter_by_time(item):
			continue
		mapped = RedditManager().map_base_to_message(item, reddit.user.me(), "Submission")
		mapped_results.insert(0, mapped)

	for elem in mapped_results:
		print(elem)


	# sorted_submissions = sorted(mapped_results, key=attrgetter('content_date_submitted_utc'))
	#
	# print(sorted_submissions)

def filter_by_time(thing: RedditBase) -> bool:
	return 12 < (datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(thing.created_utc)).total_seconds() / 3600

def chain_listing_generators(*iterables):
	# Special tool for chaining PRAW's listing generators
	# It joins the three iterables together so that we can DRY
	for it in iterables:
		for element in it:
			if element is None:
				break
			else:
				yield element


if __name__ == '__main__':
	get_sub_and_comment_forest()
