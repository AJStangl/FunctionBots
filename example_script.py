import asyncio
import os
import random
from typing import Optional, Union
from asyncpraw.models import Submission
from asyncpraw.models.comment_forest import CommentForest
from asyncpraw.reddit import Redditor, Reddit, Comment, Subreddit
import logging
import torch
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import Session
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from torch import Tensor
from transformers import GPT2Model
from simpletransformers.language_generation import LanguageGenerationModel

import shared_code
from shared_code.database.entities import Base, TrackingSubmission
from shared_code.database.repository import DataRepository
from shared_code.generators.text.model_text_generator import ModelTextGenerator
from shared_code.helpers.async_extensions import MergeAsyncIterator
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.models.bot_configuration import BotConfigurationManager, BotConfiguration
from shared_code.services.main_run_service import BotMonitorService
from shared_code.services.new_submission_service import SubmissionService
from shared_code.services.reply_service import ReplyService
from shared_code.services.text_generation import TextGenerationService
from shared_code.storage_proxies.service_proxy import QueueServiceProxy
import asyncio
from async_timeout import timeout


class Context:
	def __init__(self):
		self._user = os.environ['PsqlUser']
		self._password = os.environ['PsqlPassword']
		self._engine = create_engine(f"postgresql://{self._user}:{self._password}@localhost:5432/redditData", pool_size=32, max_overflow=-1)

	def _get_session(self):
		return Session(self._engine)

	def _close_and_dispose(self, session: Session):
		session.close()
		self._engine.dispose()

	def Add(self, entity: Base):
		session = self._get_session()
		try:
			session.add(TrackingSubmission, entity)
		except Exception as e:
			logging.error(f":: An exception has occurred in method `Add` with message {e}")
		finally:
			self._close_and_dispose(session)


async def main():
	instance = RedditManager.get_praw_instance_for_bot("PabloBot-GPT2")
	subreddit = await instance.subreddit("CoopAndPabloPlayHouse")

	comment_stream = subreddit.stream.comments()
	submission_stream = subreddit.stream.submissions()

	async for praw_item in MergeAsyncIterator(comment_stream, submission_stream, time_out=6.0):
		if isinstance(praw_item, Comment):
			comment: Comment = praw_item
			print(f"Comment {comment}")

		if isinstance(praw_item, Submission):
			submission: Submission = praw_item
			print(f"Submission {submission}")



if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	logging.getLogger(__name__)
	loop = asyncio.get_event_loop()
	future = asyncio.ensure_future(main())
	loop.run_until_complete(future)
