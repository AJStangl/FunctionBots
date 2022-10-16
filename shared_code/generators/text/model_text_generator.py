import logging
import time

import torch
from transformers import GPT2Tokenizer, GPT2LMHeadModel
from shared_code.helpers.tagging import Tagging
from shared_code.services.service_container import ServiceContainer


class ModelTextGenerator(ServiceContainer):
	def __init__(self):
		super().__init__()
		self.text_generation_parameters = {
			'max_length': 1024,
			'num_return_sequences': 1,
			'prompt': None,
			'temperature': 0.8,
			'top_k': 40,
			'top_p': .8,
			'do_sample': True,
			'repetition_penalty': 1.08,
			'stop_token': '<|endoftext|>'
		}

	def generate_text_with_no_wrapper(self, bot_username: str, prompt_text: str, cuda_device: int = 1, use_cpu: bool = True) -> str:
		start_time = time.time()
		try:
			bot_config = self.bot_configuration_manager.get_configuration_by_name(bot_username)

			# device = torch.device(f"cuda:{cuda_device}" if torch.cuda.is_available() else "cpu")
			# if not use_cpu:
			# 	cuda_device = None

			tokenizer = GPT2Tokenizer.from_pretrained(bot_config.Model)

			encoded_prompt = tokenizer.encode(prompt_text, add_special_tokens=False, return_tensors="pt")

			if len(encoded_prompt.data[0]) >= self.text_generation_parameters['max_length']:
				logging.info(
					f":: Size of Tensor {encoded_prompt.data[0]} > {self.text_generation_parameters['max_length']}. Rejecting Attempt to Process Input")
				return None

			if self.validate_text_tensor(bot_config.Model, prompt_text):
				return self.simple_transformers_generation(bot_config.Model, prompt_text, cuda_device)
			else:
				return None

			# generation_prompt = tokenizer([prompt_text], add_special_tokens=False, return_tensors="pt")
			#
			# generation_prompt = generation_prompt.to(device)
			#
			# model = GPT2LMHeadModel.from_pretrained(bot_config.Model)
			#
			# model = model.to(device)
			# output_sequences = model.generate(
			# 	inputs=generation_prompt['input_ids'],
			# 	max_length=1024,
			# 	min_length=100,
			# 	do_sample=True,
			# 	top_k=40,
			# 	temperature=0.8,
			# 	repetition_penalty=1.08,
			# 	attention_mask=generation_prompt['attention_mask'],
			# 	stop_token='<|endoftext|>',
			# )
			# text_generations = []
			#
			# for i in range(self.text_generation_parameters['num_return_sequences']):
			# 	decoded_text = tokenizer.decode(output_sequences[i], skip_special_tokens=False)
			# 	if decoded_text in ['[removed]'] or decoded_text == "":
			# 		raise Exception("Text No Good Try Again!")
			# 	text_generations.append(decoded_text)
			# 	decoded_text.replace(prompt_text, "")
			# 	print(f"Generated {i}: {decoded_text}")
			#
			# end_time = time.time()
			# duration = round(end_time - start_time, 1)
			#
			# print(f'{len(text_generations)} sample(s) of text generated in {duration} seconds.')
			#
			# return max(text_generations, key=len)

		except RuntimeError:
			logging.error(f":: An error has occurred while attempting to generate text")
			self.kill_process(cuda_device)
		except Exception as e:
			logging.error(f":: An error has occurred while attempting to generate text")
			logging.error(e)
			raise e
		finally:
			torch.cuda.empty_cache()
			pass

	def simple_transformers_generation(self, model_path: str, prompt: str, device: int):
		from simpletransformers.language_generation import LanguageGenerationModel
		model = None

		import gc
		try:
			model = LanguageGenerationModel("gpt2", model_path, use_cuda=True, cuda_device=device)
			default_text_generation_parameters = {
				'max_length': 1024,
				'num_return_sequences': 1,
				'prompt': None,
				'temperature': 0.8,
				'top_k': 40,
				'repetition_penalty': 1.008,
				'stop_token': '<|endoftext|>',
			}
			start_time = time.time()

			try:
				output_list = model.generate(prompt=prompt, args=default_text_generation_parameters)
			except RuntimeError as e:
				logging.error(f":: {e}")
				self.kill_process(device)

			end_time = time.time()
			duration = round(end_time - start_time, 1)

			logging.info(f'{len(output_list)} sample(s) of text generated in {duration} seconds.')

			if output_list:
				return output_list[0]
		except Exception as e:
			logging.error(f":: An error has occurred while attempting to generate text")
			logging.error(e)
			raise e
		finally:
			del model
			gc.collect()

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

	@staticmethod
	def clean_text_generation(text_generation: str):
		return Tagging.remove_tags_from_string(text_generation)

	def kill_process(self, device: int):
		import os
		import re
		processes = torch.cuda.list_gpu_processes(device)
		current_process = os.getpid()
		matched_process = re.findall("\s+(\d+)\s\D+", processes)
		procs = [int(proc) for proc in matched_process]
		if current_process in procs:
			logging.info(f":: Killing CUDA Task with PID: {current_process}")
			os.system(f"taskkill /F /PID {current_process}")
		else:
			logging.error(f":: No Process in {procs} can be located for running PID {current_process}")
