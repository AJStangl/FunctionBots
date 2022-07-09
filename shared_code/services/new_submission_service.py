import logging
import os
import random
from typing import Optional

from asyncpraw import Reddit
from asyncpraw.models import Submission, Subreddit

from shared_code.generators.text.model_text_generator import ModelTextGenerator
from shared_code.helpers.image_scrapper import ImageScrapper
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.helpers.tagging import TaggingMixin
from shared_code.models.bot_configuration import BotConfiguration, BotConfigurationManager


class SubmissionService:
	def __init__(self):
		self.bot_configuration_manager = BotConfigurationManager()
		self.generator: ModelTextGenerator = ModelTextGenerator()
		self.reddit_helper: RedditManager = RedditManager()
		self.scrapper: ImageScrapper = ImageScrapper()
		self.submission_interval: int = int(os.environ["SubmissionInterval"])
		self.tagging: Optional[TaggingMixin] = None

	async def invoke(self, bot_configuration: BotConfiguration) -> bool:
		logging.info(f":: Invoking Submission Service For {bot_configuration.Name}")
		instance: Reddit = self.reddit_helper.get_praw_instance_for_bot(bot_configuration.Name)
		self.tagging: TaggingMixin = TaggingMixin(instance)
		failures = []
		for target_sub in bot_configuration.SubReddits:
			last_posted_sub = await self.get_last_posted_submission(instance, target_sub)
			if last_posted_sub is None:
				last_created = 2
			else:
				last_created = RedditManager.timestamp_to_hours(last_posted_sub.created_utc)
			if last_created < self.submission_interval:
				logging.info(f":: Nice try - Time Since Last For Is {last_posted_sub} for {bot_configuration.Name} is less than {self.submission_interval}")
				continue

			logging.info(f"Time Since Last Submission to {target_sub} is {last_created}")

			image_gen_prob: int = random.randint(1, 2)
			logging.info(f":: Preparing Submission To {target_sub} for {bot_configuration.Name}")
			prompt = self.tagging.get_random_new_submission_tag(subreddit=target_sub)
			result = self.generator.generate_text(bot_username=bot_configuration.Name, prompt=prompt, default_cuda=True, num_text_generations=1)
			extracted_prompt = self.tagging.extract_submission_from_generated_text(result)

			logging.info(f":: Attempting Submission Post to {target_sub} for {bot_configuration.Name}")
			if extracted_prompt is None:
				logging.info(f":: Prompt is empty for {bot_configuration.Name}")
				failures.append(True)
				continue

			if image_gen_prob == 1:
				image_url = self.scrapper.get_image_post(bot_configuration.Name, result, self.tagging)
				new_prompt = {
					'title': extracted_prompt['title'],
					'url': image_url
				}
				try:
					logging.info(f":: Sending Image Post To {target_sub} for {bot_configuration.Name}")
					logging.info(f":: The prompt is: {extracted_prompt} for {bot_configuration.Name} to {target_sub}")
					sub: Subreddit = await instance.subreddit(target_sub)
					await sub.submit(**new_prompt)
					continue
				except Exception as e:
					logging.info(f":: Process Failed posting Image {e}")
					failures.append(True)
					continue
			else:
				try:
					logging.info(f":: Sending Text Post To {target_sub} for {bot_configuration.Name}")
					sub: Subreddit = await instance.subreddit(target_sub)
					await sub.submit(**extracted_prompt)
				except Exception as e:
					logging.info(f":: Process Failed {e}")
					failures.append(True)
					continue
			return len(failures) == 0

	async def get_last_posted_submission(self, instance: Reddit, subreddit_name: str) -> Submission:
		me = await instance.user.me()
		async for submission in me.submissions.new():
			await submission.load()
			subreddit: Subreddit = submission.subreddit
			await subreddit.load()
			if subreddit.name == subreddit_name:
				return submission
			continue

