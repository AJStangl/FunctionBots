import logging
import os
import random
from praw import Reddit
from praw.models import Submission

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
		self.tagging: TaggingMixin = TaggingMixin()
		self.scrapper: ImageScrapper = ImageScrapper()
		self.submission_interval: int = int(os.environ["SubmissionInterval"])

	def invoke(self, bot_configuration: BotConfiguration):
		logging.info(f":: Invoking Submission Service For {bot_configuration.Name}")
		instance: Reddit = self.reddit_helper.get_praw_instance_for_bot(bot_configuration.Name)
		last_posted_sub: Submission = list(instance.user.me().submissions.new())[0]
		last_created = RedditManager.timestamp_to_hours(last_posted_sub.created_utc)
		if last_created < self.submission_interval:
			logging.info(f":: Nice try - Time Since Last For Is {last_posted_sub} for {bot_configuration.Name} is less than {self.submission_interval}")
			return

		logging.info(f"Time Since Last Submission to {bot_configuration.SubReddits[0]} is {last_created}")
		image_gen_prob = random.randint(1, 2)
		target_sub = bot_configuration.SubReddits[0]
		logging.info(f":: Preparing Submission To {target_sub} for {bot_configuration.Name}")
		prompt = self.tagging.get_random_new_submission_tag(subreddit=target_sub)
		result = self.generator.generate_text(bot_username=bot_configuration.Name, prompt=prompt, default_cuda=True, num_text_generations=1)
		extracted_prompt = self.tagging.extract_submission_from_generated_text(result)

		logging.info(f":: Attempting Submission Post to {target_sub} for {bot_configuration.Name}")
		if extracted_prompt is None:
			logging.info(f":: Prompt is empty for {bot_configuration.Name}")
			return

		if image_gen_prob == 1:
			image_url = self.scrapper.get_image_post(bot_configuration.Name, result)
			new_prompt = {
				'title': extracted_prompt['title'],
				'url': image_url
			}
			try:
				logging.info(f":: Sending Image Post To {target_sub} for {bot_configuration.Name}")
				logging.info(f":: The prompt is: {extracted_prompt} for {bot_configuration.Name} to {target_sub}")
				sub = instance.subreddit(target_sub)
				sub.submit(**new_prompt)
				return
			except Exception as e:
				logging.info(f":: Process Failed posting Image {e}")
				return
		else:
			try:
				logging.info(f":: Sending Text Post To {target_sub} for {bot_configuration.Name}")
				sub = instance.subreddit(target_sub)
				sub.submit(**extracted_prompt)
			except Exception as e:
				logging.info(f":: Process Failed {e}")
				return
