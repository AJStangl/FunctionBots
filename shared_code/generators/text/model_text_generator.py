import logging
import random
import time

from torch import nn
from transformers import GPT2Tokenizer, GPT2LMHeadModel
import torch

from shared_code.helpers.tagging import Tagging
from shared_code.services.service_container import ServiceContainer


class ModelTextGenerator(ServiceContainer):
	def __init__(self):
		super().__init__()
		self.text_generation_parameters = {
			'max_length': 1024,
			'num_return_sequences': 5,
			'prompt': None,
			'temperature': 0.8,
			'top_k': 40,
			'top_p': .75,
			'do_sample': True,
			'repetition_penalty': 1.08,
			'stop_token': '<|endoftext|>'
		}

	def generate_text_with_no_wrapper(self, bot_username: str, prompt_text: str):
		model = None
		encoded_prompt = None
		start_time = time.time()
		try:
			bot_config = self.bot_configuration_manager.get_configuration_by_name(bot_username)

			devices = [
				torch.device("cuda:0" if torch.cuda.is_available() else "cpu"),
				torch.device("cuda:1" if torch.cuda.is_available() else "cpu"),
				torch.device("cuda:2" if torch.cuda.is_available() else "cpu")]

			random_device_index = str(random.randint(0, torch.cuda.device_count() - 1))
			device = torch.device(f"cuda:{random_device_index}")

			tokenizer = GPT2Tokenizer.from_pretrained(bot_config.Model)

			encoded_prompt = tokenizer.encode(prompt_text, add_special_tokens=False, return_tensors="pt")

			if len(encoded_prompt.data[0]) > self.text_generation_parameters['max_length']:
				logging.info(
					f":: Size of Tensor {encoded_prompt.data[0]} > {self.text_generation_parameters['max_length']}. Rejecting Attempt to Process Input")
				return ''

			encoded_prompt = encoded_prompt.to(device)

			model = GPT2LMHeadModel.from_pretrained(bot_config.Model)

			model = model.to(device)

			output_sequences = model.generate(
				input_ids=encoded_prompt,
				max_length=self.text_generation_parameters['max_length'],
				temperature=self.text_generation_parameters['temperature'],
				top_k=self.text_generation_parameters['top_k'],
				top_p=self.text_generation_parameters['top_p'],
				repetition_penalty=self.text_generation_parameters['repetition_penalty'],
				do_sample=self.text_generation_parameters['do_sample'],
				num_return_sequences=self.text_generation_parameters['num_return_sequences'],
			)

			text_generations = []

			for i in range(self.text_generation_parameters['num_return_sequences']):
				decoded_text = tokenizer.decode(output_sequences[i], skip_special_tokens=False)
				text_generations.append(decoded_text)
				logging.info(f"Generated {i}: {tokenizer.decode(output_sequences[i], skip_special_tokens=False)}")

			end_time = time.time()
			duration = round(end_time - start_time, 1)

			logging.info(f'{len(text_generations)} sample(s) of text generated in {duration} seconds.')

			return max(text_generations, key=len)

		except Exception as e:
			logging.error(f":: An error has occurred while attempting to generate text")
			logging.error(e)
		finally:
			if model is not None:
				model = model.to("cpu")
				del model
			if encoded_prompt is not None:
				encoded_prompt = encoded_prompt.to("cpu")
				del encoded_prompt
			torch.cuda.empty_cache()

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
