import logging
import os
import time
from transformers import GPT2Tokenizer, GPT2LMHeadModel
import torch
import re

from simpletransformers.language_generation import LanguageGenerationModel

from shared_code.models.bot_configuration import BotConfigurationManager


class ModelTextGenerator(object):
	def __init__(self):
		self.default_text_generation_parameters = {
			'max_length': 1024,
			'num_return_sequences': 0,
			'prompt': None,
			'temperature': 0.8,
			'top_k': 40,
			'repetition_penalty': 1.008,
			'stop_token': '<|endoftext|>',
		}

	def generate_text(self, bot_username, prompt, default_cuda: bool = True, num_text_generations: int = 3) -> str:
		start_time = time.time()
		config = BotConfigurationManager().get_configuration_by_name(bot_username)

		self.default_text_generation_parameters['num_return_sequences'] = num_text_generations

		if default_cuda:
			use_gpu = os.environ["Cuda"]
		else:
			use_gpu = False
		try:
			if not self.validate_text_tensor(model_path=config.Model, prompt=prompt):
				logging.info(f"Prompt For {config.Model} fails to validate tensor equality")
				return ''

			model = LanguageGenerationModel("gpt2", config.Model, use_cuda=bool(use_gpu))
			output_list = model.generate(prompt=prompt, args=self.default_text_generation_parameters)

			end_time = time.time()
			duration = round(end_time - start_time, 1)

			logging.info(f'{len(output_list)} sample(s) of text generated in {duration} seconds.')

			if output_list:
				return max(output_list, key=len)

		except Exception as e:
			logging.error(f"{e} - Killing CUDA")
			self._kill_bad_cuda()


	def generate_text_with_no_wrapper(self, bot_username, prompt_text, default_cuda: bool = True, num_text_generations: int = 3):
		model = None
		encoded_prompt = None
		start_time = time.time()
		bot_configuration_manager: BotConfigurationManager = BotConfigurationManager()
		try:
			text_generation_parameters = {
				'max_length': 1024,
				'num_return_sequences': 0,
				'prompt': None,
				'temperature': 0.8,
				'top_k': 40,
				'repetition_penalty': 1.008,
				'stop_token': '<|endoftext|>'
			}
			bot_config = bot_configuration_manager.get_configuration_by_name(bot_username)

			tokenizer = GPT2Tokenizer.from_pretrained(bot_config.Model)

			device = torch.device('cuda')

			encoded_prompt = tokenizer.encode(prompt_text, add_special_tokens=False, return_tensors="pt")

			if len(encoded_prompt.data[0]) > text_generation_parameters['max_length']:
				logging.info(
					f":: Size of Tensor {encoded_prompt.data[0]} > {text_generation_parameters['max_length']}. Rejecting Attempt to Process Input")
				return ''

			encoded_prompt = encoded_prompt.to(device)

			model = GPT2LMHeadModel.from_pretrained(bot_config.Model)

			model = model.to(device)

			output_sequences = model.generate(
				input_ids=encoded_prompt,
				max_length=1024,
				temperature=0.8,
				top_k=40,
				top_p=0.84,
				repetition_penalty=1.008,
				do_sample=True,
				num_return_sequences=1
			)

			text = tokenizer.decode(output_sequences[0], skip_special_tokens=False)

			end_time = time.time()
			duration = round(end_time - start_time, 1)

			logging.info(f'{1} sample(s) of text generated in {duration} seconds.')

			return text

		except Exception as e:
			logging.error(f":: An error has occurred while attempting to generate text")
			logging.error(e)
		finally:
			if model is not None:
				model = model.to("cpu")
			if encoded_prompt is not None:
				encoded_prompt = encoded_prompt.to("cpu")
				del encoded_prompt
			torch.cuda.empty_cache()

	@staticmethod
	def _kill_bad_cuda():
		processes = torch.cuda.list_gpu_processes()
		current_process = os.getpid()
		matched_process = re.findall("\s+(\d+)\s\D+", processes)
		procs = [int(proc) for proc in matched_process]
		if current_process in procs:
			logging.info(f":: Killing CUDA Task with PID: {current_process}")
			os.system(f"taskkill /F /PID {current_process}")
		else:
			logging.error(f":: No Process in {procs} can be located for running PID {current_process}")

	@staticmethod
	def validate_text_tensor(model_path, prompt):
		prompt_text = prompt
		tokenizer = GPT2Tokenizer.from_pretrained(model_path)
		tokens = tokenizer.tokenize(prompt_text)
		if len(tokens) > 1024:
			logging.info(f":: Tokens for {model_path} is > {1024}. Skipping model generation")
			return False
		encoded_prompt = tokenizer.encode(prompt_text, add_special_tokens=False, return_tensors="pt")
		h_tensor = encoded_prompt.H
		t_tensor = encoded_prompt.T
		h = [item for item in h_tensor]
		t = [item for item in t_tensor]
		if len(h) == len(t):
			return True
		else:
			logging.info(f":: Size of T Tensor {len(h)} is not equal to H tensor {len(h)}. Skipping model Generation")
			return False
