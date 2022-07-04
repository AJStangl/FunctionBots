import logging
import azure.functions as func
import random

from praw.reddit import Submission

from shared_code.generators.text.model_text_generator import ModelTextGenerator
from shared_code.helpers.reddit_helper import RedditManager
from shared_code.helpers.tagging import TaggingMixin
from shared_code.models.bot_configuration import BotConfigurationManager, BotConfiguration
from shared_code.helpers.image_scrapper import ImageScrapper


def main(submissionTimer: func.TimerRequest) -> None:
	logging.info(f":: Submission Creation Trigger Called")

	manager: BotConfigurationManager = BotConfigurationManager()

	generator: ModelTextGenerator = ModelTextGenerator()

	reddit_helper: RedditManager = RedditManager()

	tagging: TaggingMixin = TaggingMixin()

	scrapper: ImageScrapper = ImageScrapper()

	configs: [BotConfiguration] = list(filter(manager.filter_configuration, manager.get_configuration()))

	random.shuffle(configs)

	bot: BotConfiguration = configs[0]

	for sub in bot.SubReddits:
		instance = reddit_helper.get_praw_instance_for_bot(bot.Name)
		last_posted_sub: Submission = list(instance.user.me().submissions.new())[0]
		last_created_time_utc = RedditManager.timestamp_to_hours(last_posted_sub.created_utc) - 4
		if last_created_time_utc < 1:
			logging.info(f":: Nice try - Time Since Last For Is {last_posted_sub} for {bot.Name}")
			continue

		image_gen_prob = random.randint(1, 2)
		target_sub = sub
		prompt = tagging.get_random_new_submission_tag(subreddit=sub)
		result = generator.generate_text(bot.Name, prompt, True, 1)
		extracted_prompt = tagging.extract_submission_from_generated_text(result)

		logging.info(f":: Submitting Post to {target_sub} for {bot.Name}")

		if extracted_prompt is None:
			logging.info(f":: Prompt is empty for {bot.Name}")
			continue

		if image_gen_prob == 1:
			image_url = scrapper.get_image_post(bot.Name, result)
			new_prompt = {
				'title': extracted_prompt['title'],
				'url': image_url
			}
			try:
				logging.info(f":: The prompt is: {extracted_prompt} for {bot.Name} to {target_sub}")
				sub = instance.subreddit(target_sub)
				sub.submit(**new_prompt)
				continue
			except Exception as e:
				logging.info(f":: Process Failed posting Image {e}")
				continue
		else:
			try:
				logging.info(f":: The prompt is: {extracted_prompt} for {bot.Name} to {target_sub}")
				sub = instance.subreddit(target_sub)
				sub.submit(**extracted_prompt)
			except Exception as e:
				logging.info(f":: Process Failed {e}")
				continue

	return None
