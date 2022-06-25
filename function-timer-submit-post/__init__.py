import logging
import time
import azure.functions as func
import random
from shared_code.generators.text.model_text_generator import ModelTextGenerator
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.helpers.tagging import TaggingMixin
from shared_code.models.bot_configuration import BotConfigurationManager
from shared_code.helpers.image_scrapper import ImageScrapper

def main(submissionTimer: func.TimerRequest) -> None:
	logging.info(f":: Submission Trigger Called at {time.time()}")
	manager = BotConfigurationManager()
	generator = ModelTextGenerator()
	reddit_helper = RedditManager()
	tagging: TaggingMixin = TaggingMixin()
	scrapper: ImageScrapper = ImageScrapper()

	configs = list(filter(manager.filter_configuration, manager.get_configuration()))

	for bot in configs:
		for sub in bot.SubReddits:
			image_gen_prob = random.randint(1, 3)
			logging.info(f":: Starting Submission For {bot.Name} to {sub}")
			target_sub = sub
			prompt = tagging.get_random_new_submission_tag(subreddit=sub)
			result = generator.generate_text(bot.Name, prompt, True)
			extracted_prompt = tagging.extract_submission_from_generated_text(result)
			instance = reddit_helper.get_praw_instance_for_bot(bot.Name)
			latest_sub = next(instance.user.me.submissions.new())

			logging.debug(f":: Submitting Post to {target_sub} for {bot.Name}")

			if extracted_prompt is None:
				logging.debug(f":: Prompt is empty for {bot.Name}")
				continue

			if image_gen_prob == 1:
				image_url = scrapper.get_image_post(bot.Name, result)
				new_prompt = {
					'title': extracted_prompt['title'],
					'url': image_url
				}
				try:
					logging.debug(f":: The prompt is: {extracted_prompt} for {bot.Name} to {target_sub}")
					sub = instance.subreddit(target_sub)
					sub.submit(**new_prompt)
					continue
				except Exception as e:
					logging.error(f":: Process Failed posting Image {e}")
			else:
				try:
					logging.debug(f":: The prompt is: {extracted_prompt} for {bot.Name} to {target_sub}")
					sub = instance.subreddit(target_sub)
					sub.submit(**extracted_prompt)
				except Exception as e:
					logging.error(f":: Process Failed {e}")

	return None
