import logging
from typing import Optional

from asyncpraw import Reddit

from shared_code.database.repository import DataRepository
from shared_code.helpers.image_scrapper import ImageScrapper
from shared_code.helpers.mapping_models import Mapper
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.helpers.reply_logic import ReplyLogic
from shared_code.helpers.tagging import Tagging
from shared_code.models.bot_configuration import BotConfigurationManager
from shared_code.services.reply_service import ReplyService
from shared_code.storage_proxies.service_proxy import QueueServiceProxy


class ServiceContainer(object):
	def __init__(self):
		self.set_logger(__name__)
		self.reddit_helper: RedditManager = RedditManager()
		self.repository: DataRepository = DataRepository()
		self.queue_proxy: QueueServiceProxy = QueueServiceProxy()
		self.reply_service: ReplyService = ReplyService()
		self.bot_configuration_manager: BotConfigurationManager = BotConfigurationManager()
		self.table_helper: Mapper = Mapper()
		self.scrapper: ImageScrapper = ImageScrapper()
		self.reddit_instance: Optional[Reddit] = None
		self.tagging: Optional[Tagging] = None
		self.reply_logic: Optional[ReplyLogic] = None

	def set_reddit_instance(self, bot_name: str) -> None:
		self.reddit_instance: Reddit = self.reddit_helper.get_praw_instance_for_bot(bot_name)
		self.tagging = Tagging(self.reddit_instance)
		self.reply_logic = ReplyLogic(self.reddit_instance)

	async def close_reddit_instance(self) -> None:
		await self.reddit_instance.close()

	def set_tagging(self):
		self.tagging = Tagging(self.reddit_instance)

	def set_logger(self, logger_name: str):
		# Create logger
		logger = logging.getLogger(logger_name)
		logger.setLevel(logging.INFO)

		# create the stream
		ch = logging.StreamHandler()
		ch.setLevel(logging.INFO)

		# create formatter
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

		# add formatter to ch
		ch.setFormatter(formatter)

		# add ch to logger
		logger.addHandler(ch)

		self.logger = logger

		return
