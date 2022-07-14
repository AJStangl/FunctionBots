import asyncio
import random
from typing import Optional, Union
from asyncpraw.models import Submission
from asyncpraw.models.comment_forest import CommentForest
from asyncpraw.reddit import Redditor, Reddit, Comment, Subreddit
import logging
import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from torch import Tensor
from transformers import GPT2Model
from simpletransformers.language_generation import LanguageGenerationModel

from shared_code.database.repository import DataRepository
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.models.bot_configuration import BotConfigurationManager, BotConfiguration
from shared_code.services.main_run_service import BotMonitorService
from shared_code.services.new_submission_service import SubmissionService
from shared_code.services.reply_service import ReplyService
from shared_code.storage_proxies.service_proxy import QueueServiceProxy


async def main():
	pass


if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	logging.getLogger(__name__)
	loop = asyncio.get_event_loop()
	future = asyncio.ensure_future(main())
	loop.run_until_complete(future)