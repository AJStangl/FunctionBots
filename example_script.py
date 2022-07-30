import asyncio
import os
import time
import random
from typing import Optional, Union
from asyncpraw.models import Submission, Comment
from asyncpraw.models.comment_forest import CommentForest
from asyncpraw.reddit import Redditor, Reddit, Subreddit
import logging
import torch
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import Session
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from torch import Tensor
from transformers import GPT2Model
from simpletransformers.language_generation import LanguageGenerationModel
from datetime import datetime
import shared_code
from shared_code.database.context import Context
from shared_code.database.entities import Base, TrackingSubmission, TrackingComment, TrackingResponse
from shared_code.database.repository import DataRepository
from shared_code.generators.text.model_text_generator import ModelTextGenerator
from shared_code.helpers.merge_async_iterator import MergeAsyncIterator
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.helpers.tagging import Tagging
from shared_code.models.bot_configuration import BotConfigurationManager, BotConfiguration
from shared_code.services.main_run_service import BotMonitorService
from shared_code.services.new_submission_service import SubmissionService
from shared_code.services.reply_service import ReplyService
from shared_code.services.text_generation import TextGenerationService
from shared_code.storage_proxies.service_proxy import QueueServiceProxy
import asyncio
from async_timeout import timeout


def tag_submission(submission: Submission, tag_override: str = os.environ["SubNameOverride"]) -> str:
		tagged_text = ""
		if not isinstance(submission, Submission):
			return tagged_text

		if submission.is_self:
			tagged_text += "<|soss"
		else:
			tagged_text += "<|sols"

		if tag_override is not None:
			tagged_text += f" r/{tag_override}|>"
		else:
			tagged_text += f" r/{submission.subreddit}|>"

		# prepend the tagged text
		if submission.is_self:

			selftext = submission.selftext

			if hasattr(submission, 'poll_data'):
				for option in submission.poll_data.options:
					selftext += f" - {option.text}"

			# selftext submission
			tagged_text += f"<|sot|>{submission.title}<|eot|><|sost|>{selftext}<|eost|>"

		else:
			# it's a link submission
			tagged_text += f"<|sot|>{submission.title}<|eot|><|sol|><|eol|>"

		return tagged_text


async def add_submission_to_table(submission: Submission, context: Context) -> Union[TrackingSubmission, None]:
	bots = BotConfigurationManager().get_bot_name_list()
	session = context.get_session()
	entity = TrackingSubmission()
	entity.Id = submission.id
	entity.Text = tag_submission(submission)
	entity.SubmissionTimestamp = datetime.fromtimestamp(submission.created_utc)
	entity.Subreddit = submission.subreddit.display_name
	entity.Author = getattr(submission.author, 'name', '')
	entity.DateCreated = datetime.now()
	entity.DateUpdated = datetime.now()
	result = context.add(entity, session)
	if result is None:
		logging.info(f":: Added {type(submission)} To Table for {submission.id}")
		# Create Entry For Tracking Comment Responses.
		for bot in bots:
			tracking_response = TrackingResponse()
			tracking_response.Id = f"{bot}|{entity.Id}"
			tracking_response.BotName = bot
			tracking_response.SubmissionId = entity.Id,
			tracking_response.CommentId = ""
			tracking_response.HasResponded = False
			tracking_response.DateCreated = datetime.now()
			tracking_response.DateUpdated = datetime.now()
			context.add(tracking_response, session)
		context.close_and_dispose(session)
		return entity

	context.close_and_dispose(session)


async def add_comment_to_table(comment: Comment, context: Context) -> Union[TrackingComment, None]:
	bots: [BotConfiguration] = BotConfigurationManager().get_bot_name_list()
	session: Session = context.get_session()
	entity = TrackingComment()
	entity.Id = comment.id
	entity.SubmissionId = comment.submission.id
	entity.CommentTimestamp = datetime.fromtimestamp(comment.created_utc)
	entity.Author = getattr(comment.author, 'name', '')
	entity.ParentId = comment.parent_id
	entity.Text = ""
	entity.DateCreated = datetime.now()
	entity.DateUpdated = datetime.now()
	result = context.add(entity, session)
	if result is None:
		logging.info(f":: Added {type(comment)} To Table for {comment.id}")
		for bot in bots:
			tracking_response = TrackingResponse()
			tracking_response.Id = f"{bot}|{entity.Id}"
			tracking_response.BotName = bot
			tracking_response.SubmissionId = "",
			tracking_response.CommentId = entity.Id
			tracking_response.HasResponded = False
			tracking_response.DateCreated = datetime.now()
			tracking_response.DateUpdated = datetime.now()
			context.add(tracking_response, session)
		context.close_and_dispose(session)
		return entity
	context.close_and_dispose(session)


async def function_for_general_polling_on_timer():
	instance = RedditManager.get_praw_instance_for_bot("PabloBot-GPT2")
	subreddit = await instance.subreddit("CoopAndPabloPlayHouse")
	context: Context = Context()
	comment_stream = subreddit.stream.comments()
	submission_stream = subreddit.stream.submissions()
	time_out_for_iteration: float = float(os.environ["TimeoutForSearchIterator"])

	logging.info(f":: Streaming Comments For {time_out_for_iteration} seconds")
	start_time = time.time()
	async for praw_item in MergeAsyncIterator(submission_stream, comment_stream, time_out=time_out_for_iteration):
		if isinstance(praw_item, Comment):
			logging.info(f":: Handling Comment {praw_item} from stream")
			comment: Comment = praw_item
			await add_comment_to_table(comment, context)

		if isinstance(praw_item, Submission):
			logging.info(f":: Handling Submission {praw_item} from stream")
			submission: Submission = praw_item
			await add_submission_to_table(submission, context)

	end_time = time.time()
	duration = round(end_time - start_time, 1)
	logging.info(f"Total Duration for Processing: {duration}")
	await instance.close()


async def function_that_handles_comment_collation_and_initialization():
	instance: Reddit = RedditManager.get_praw_instance_for_bot("PabloBot-GPT2")
	tagging: Tagging = Tagging(instance)
	context: Context = Context()
	session: Session = context.get_session()
	entities: [] = context.get_comments_for_processing(session, limit=30)
	logging.info(f":: Processing {len(entities)} Comment Text Values")
	comment_ids = []
	for entity in entities:
		comment_id = entity.Id
		comment_ids.append(comment_id)
		submission_id = entity.SubmissionId
		comment: Comment = await instance.comment(id=comment_id, fetch=True)
		submission: Submission = await instance.submission(id=submission_id, fetch=True)
		text = await tagging.tag_comment_with_sub(comment, submission)
		entity.Text = text
		session.commit()
	context.close_and_dispose(session)
	await instance.close()


async def function_that_sends_thing_for_text_generation():
	context: Context = Context()
	session: Session = context.get_session()
	bot_name = "PabloBot-GPT2"
	results = context.get_items_ready_for_text_generation(bot_name, session, 10)
	for elem in results:
		logging.info(results)


if __name__ == '__main__':
	# First fire off a method that generally pulls in the reddit data
	# - This should run for as long as possible.
	# - function_for_general_polling_on_timer()
	# At the same time Fire Off This Method:
	# - function_that_handles_comment_collation_and_initialization()
	# This above method will prime the database in a threadsafe manner for the more intense calls to reddit.
	# Finally, there needs to be a method that is triggered by new events written to the TrackingResponse table.
	# 1 Message per write. This message will invoke a call to the table for a specific bot, calculate if it should
	# respond, and send a message to a worker. The message should have the bot name and the id of the
	# - function_that_sends_thing_for_text_generation
	logging.basicConfig(level=logging.INFO)
	logging.getLogger(__name__)
	loop = asyncio.get_event_loop()
	future = asyncio.ensure_future(function_that_sends_thing_for_text_generation())
	loop.run_until_complete(future)
