import logging
import os
import random

from asyncpraw import Reddit
from asyncpraw.models import Submission, Subreddit

from shared_code.generators.text.model_text_generator import ModelTextGenerator
from shared_code.models.bot_configuration import BotConfiguration
from shared_code.services.service_container import ServiceContainer


class SubmissionService(ServiceContainer):
	def __init__(self):
		super().__init__()
		self.submission_interval: int = int(os.environ["SubmissionInterval"])

	async def invoke(self, bot_configuration: BotConfiguration) -> bool:
		try:
			model_text_generation: ModelTextGenerator = ModelTextGenerator()
			logging.info(f":: Invoking Submission Service For {bot_configuration.Name}")
			self.set_reddit_instance(bot_configuration.Name)
			target_sub = bot_configuration.SubReddits[0]

			image_gen_prob: int = random.randint(1, 100)
			logging.info(f":: Preparing Submission To {target_sub} for {bot_configuration.Name}")
			prompt = self.tagging.get_random_new_submission_tag(subreddit=os.environ["SubNameOverride"])
			result = model_text_generation.generate_text_with_no_wrapper(bot_username=bot_configuration.Name, prompt_text=prompt, cuda_device=1)
			extracted_prompt = self.tagging.extract_submission_from_generated_text(result)

			logging.info(f":: Attempting Submission Post to {target_sub} for {bot_configuration.Name}")
			if extracted_prompt is None:
				logging.info(f":: Prompt is empty for {bot_configuration.Name}")
				return False

			if image_gen_prob > 70:
				image_url = self.scrapper.get_image_post(bot_configuration.Name, result, self.tagging)
				new_prompt = {
					'title': extracted_prompt['title'],
					'url': image_url
				}
				try:
					logging.info(f":: Sending Image Post To {target_sub} for {bot_configuration.Name}")
					logging.info(f":: The prompt is: {extracted_prompt} for {bot_configuration.Name} to {target_sub}")
					sub: Subreddit = await self.reddit_instance.subreddit(target_sub)
					await sub.submit(**new_prompt)
					return True
				except Exception as e:
					logging.info(f":: Process Failed posting Image {e}")
					return False
			else:
				try:
					logging.info(f":: Sending Text Post To {target_sub} for {bot_configuration.Name}")
					sub: Subreddit = await self.reddit_instance.subreddit(target_sub)
					await sub.submit(**extracted_prompt)
				except Exception as e:
					logging.info(f":: Process Failed {e}")
					return False
			return True
		finally:
			await self.close_reddit_instance()

	@staticmethod
	async def get_last_posted_submission(instance: Reddit, subreddit_name: str) -> Submission:
		me = await instance.user.me()
		async for submission in me.submissions.new():
			await submission.load()
			subreddit: Subreddit = submission.subreddit
			await subreddit.load()
			if subreddit.name == subreddit_name:
				return submission
			continue


