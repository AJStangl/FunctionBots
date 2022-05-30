import logging
import time
from random import random
from typing import Optional
import re
import azure.functions as func
import codecs
import ftfy

from shared_code.generators.text.model_text_generator import ModelTextGenerator
from shared_code.helpers.reddit_helper import RedditHelper
from shared_code.models.bot_configuration import BotConfigurationManager, BotConfiguration

_link_submission_start_tag = '<|sols|>'
_selftext_submission_start_tag = '<|soss|>'

_title_start_tag = '<|sot|>'
_selftext_start_tag = '<|sost|>'

_reply_start_tag = '<|sor|>'
_reply_end_tag = '<|eor|>'

_end_tag = '<|'

def main(submissionTimer: func.TimerRequest) -> None:
	logging.info(f":: Submission Trigger Called at {time.time()}")
	return
	manager = BotConfigurationManager()
	generator = ModelTextGenerator()
	reddit_helper = RedditHelper()

	configs = list(filter(manager.filter_configuration, manager.get_configuration()))

	for bot in configs:
		logging.info(f":: Starting Submission For {bot.Name} to {bot.SubReddits[0]}")
		target_sub = bot.SubReddits[0]
		prompt = _get_random_new_submission_tag()
		result = generator.generate_text(bot.Name, prompt)

		extracted_prompt = extract_submission_from_generated_text(result)

		if extracted_prompt is None:
			logging.debug(f":: Prompt is empty for {bot.Name}")
			continue

		#TODO: Handle Image Posts -- We don't do that now
		instance = reddit_helper.get_praw_instance(bot.Name)
		logging.debug(f":: Submitting Post to {target_sub} for {bot.Name}")
		try:
			logging.debug(f":: The prompt is{extracted_prompt}")
			foo = instance.subreddit(target_sub).submit(**extracted_prompt)
			logging.debug(foo)
		except Exception as e:
			logging.error(f":: Process Failed {e}")

	return None


def get_random_new_submission_tag(botconfig: BotConfiguration) -> str:
	random_value = random()
	tag = ''

	# Make a text post
	tag += '<|soss'

	# TODO: Fix
	tag += f' r/{botconfig.SubReddits[0]}|>'

	return tag + '<|sot|>'


def extract_title_from_generated_text(generated_text):
	idx_title_start = generated_text.find(_title_start_tag)
	idx_title_end = generated_text.find(_end_tag, (idx_title_start + len(_title_start_tag)))

	if idx_title_start == -1 or idx_title_end == -1:
		# There must be at least a complete title to make a submission
		return None

	title_text = generated_text[idx_title_start + len(_title_start_tag):idx_title_end]

	if (0 < len(title_text) < 300):
		# Validate the title length is within reddit's range
		return _decode_generated_text(title_text)


def extract_selftext_from_generated_text(generated_text):
	idx_st_start = generated_text.find(_selftext_start_tag)
	idx_st_end = generated_text.find(_end_tag, (idx_st_start + len(_selftext_start_tag)))

	if idx_st_start == -1 or idx_st_end == -1:
		return None

	selftext_text = generated_text[idx_st_start + len(_selftext_start_tag):idx_st_end]
	return _decode_generated_text(selftext_text)


def extract_submission_from_generated_text(generated_text):
	return_dict = {}

	# remove any cruft
	generated_text = generated_text.replace('&amp;#x200B;\n', '')

	title = extract_title_from_generated_text(generated_text)

	if not title:
		return {}
	else:
		# The title is ok, add it to the dict to return
		return_dict['title'] = title

	selftext = extract_selftext_from_generated_text(generated_text)

	if selftext:
		return_dict['selftext'] = selftext

	return return_dict


def remove_tags_from_string(input_string):
	# Removes any <|sor u/user|>, <|sost|> etc from a string
	return re.sub(r'(\<\|[\w\/ ]*\|\>)', ' ', input_string).strip()


def _decode_generated_text(text):
	return ftfy.fix_text(codecs.decode(text, "unicode_escape"))


def _get_random_new_submission_tag():
	return '<|soss|><|sot|>'



