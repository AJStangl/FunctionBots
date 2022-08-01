import datetime
import logging

from azure.core.paging import ItemPaged
from azure.storage.queue import QueueServiceClient, QueueClient, QueueMessage
from asyncpraw import Reddit
from asyncpraw.models import Submission, Comment
from sqlalchemy.orm import Session

from shared_code.database.table_record import TableRecord
from shared_code.helpers.record_helper import TableHelper
from shared_code.database.repository import DataRepository
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.helpers.tagging import Tagging
from shared_code.storage_proxies.service_proxy import QueueServiceProxy


class ReplyService:
	def __init__(self):
		self.logging = logging.getLogger(__name__)
		self.bad_key_words = ["removed", "nouniqueideas007", "ljthefa"]
		self.reddit_manager: RedditManager = RedditManager()
		self.queue_service: QueueServiceClient = QueueServiceProxy().service
		self.repository: DataRepository = DataRepository()
		self.queue_client: QueueClient = self.queue_service.get_queue_client("reply-queue")

	async def handle_message(self, message):
		self.logging.info(f":: Handling Messages From Iterator")
		session: Session = self.repository.get_session()
		manager: RedditManager = RedditManager()

		record: TableRecord = TableHelper.handle_fucking_bullshit(message)

		prompt: str = record["TextGenerationPrompt"]

		response: str = record["TextGenerationResponse"]

		reddit: Reddit = manager.get_praw_instance_for_bot(record["RespondingBot"])

		try:
			tagging: Tagging = Tagging(reddit)

			extract: dict = tagging.extract_reply_from_generated_text(prompt, response)

			entity: TableRecord = self.repository.get_by_id_with_session(session, record["Id"])

			body = None
			try:
				body = extract['body']
			except Exception as e:
				logging.info(f":: Has No Body {entity.Id}")
				return

			if record is None:
				return

			if body is None:
				logging.info(f":: No Body Present for message")
				return

			for item in self.bad_key_words:
				if body in item:
					logging.info(f"Response has negative keyword - {item}")
					entity.HasResponded = True
					entity.Status = 3
					entity.RepliedAt = datetime.datetime.now()
					session.commit()
					continue

			if entity.InputType == "Submission":
				sub_instance: Submission = await reddit.submission(id=entity.RedditId)
				logging.info(f":: Sending Out Reply To Submission - {entity.RedditId}")
				await sub_instance.reply(body)
				entity.HasResponded = True
				entity.Status = 4
				entity.RepliedAt = datetime.datetime.now()
				entity.TextGenerationResponse = body
				session.commit()
				return

			if entity.InputType == "Comment":
				logging.info(f":: Sending Out Reply To Comment - {entity.RedditId}")
				comment_instance: Comment = await reddit.comment(id=entity.RedditId)
				await comment_instance.reply(body)
				entity.HasResponded = True
				entity.Status = 4
				entity.RepliedAt = datetime.datetime.now()
				entity.TextGenerationResponse = body
				session.commit()
				return

		except Exception as e:
			logging.error(e)
		finally:
			session.close()
			await reddit.close()
