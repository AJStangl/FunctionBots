from typing import Optional

from asyncpraw import Reddit

from shared_code.database.repository import DataRepository
from shared_code.helpers.record_helper import TableHelper
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.helpers.reply_logic import ReplyLogic
from shared_code.helpers.tagging import Tagging
from shared_code.models.bot_configuration import BotConfigurationManager
from shared_code.services.reply_service import ReplyService
from shared_code.storage_proxies.service_proxy import QueueServiceProxy


class ServiceContainer(object):
	def __init__(self):
		self.reddit_helper: RedditManager = RedditManager()
		self.repository: DataRepository = DataRepository()
		self.queue_proxy: QueueServiceProxy = QueueServiceProxy()
		self.reply_service: ReplyService = ReplyService()
		self.bot_configuration_manager: BotConfigurationManager = BotConfigurationManager()
		self.table_helper: TableHelper = TableHelper()
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


