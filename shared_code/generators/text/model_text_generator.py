import logging
import os
import time
from simpletransformers.language_generation import LanguageGenerationModel
from shared_code.models.bot_configuration import BotConfigurationManager, BotConfiguration


class ModelTextGenerator(object):
	def __init__(self):
		self.default_text_generation_parameters = {
			'max_length': 1024,
			'num_return_sequences': 1,
			'prompt': None,
			'temperature': 0.8,
			'top_k': 40,
			'repetition_penalty': 1.008,
			'stop_token': '<|endoftext|>',
		}

	def generate_text(self, bot_username, prompt) -> str:
		start_time = time.time()
		config = BotConfigurationManager().get_configuration_by_name(bot_username)

		use_gpu = os.environ["Cuda"]
		try:
			model = LanguageGenerationModel("gpt2", config.Model, use_cuda=bool(use_gpu))
			output_list = model.generate(prompt=prompt, args=self.default_text_generation_parameters)

			end_time = time.time()
			duration = round(end_time - start_time, 1)

			logging.info(f'{len(output_list)} sample(s) of text generated in {duration} seconds.')

			if output_list:
				return output_list[0]

		except Exception as e:
			logging.error(f"{e} - Killing CUDA")
			self._kill_bad_cuda()

	@staticmethod
	def _kill_bad_cuda():
		import torch
		import re
		import os
		processes = torch.cuda.list_gpu_processes()
		matched_process = re.findall("\s+(\d+)\s\D+", processes)
		if len(matched_process) != 0:
			kill_process = matched_process[0]
			logging.info(f":: Killing CUDA Task with PID: {kill_process}")
			os.system(f"taskkill /F /PID {kill_process}")
