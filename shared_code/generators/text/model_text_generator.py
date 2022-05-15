import logging
import time
from simpletransformers.language_generation import LanguageGenerationModel


class ModelTextGenerator(object):
	def __init__(self):
		self.default_text_generation_parameters = {
			'max_length': 512,
			'num_return_sequences': 1,
			'prompt': None,
			'temperature': 0.8,
			'top_k': 40,
			'repetition_penalty': 1.008,
			'stop_token': '<|endoftext|>',
		}

	def generate_text(self, bot_username, prompt) -> str:

		model = LanguageGenerationModel("gpt2", "D:\\models\\large_larissa_bot", use_cuda=False)

		start_time = time.time()

		# pop the prompt out from the args
		output_list = model.generate(prompt=prompt, args=self.default_text_generation_parameters)

		end_time = time.time()
		duration = round(end_time - start_time, 1)

		logging.info(f'{len(output_list)} sample(s) of text generated in {duration} seconds.')

		if output_list:
			return output_list[0]
