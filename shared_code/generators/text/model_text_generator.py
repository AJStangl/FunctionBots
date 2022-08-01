import logging
import time

import torch
from simpletransformers.language_generation import LanguageGenerationModel
from transformers import GPT2Tokenizer, GPT2LMHeadModel

from shared_code.models.bot_configuration import BotConfigurationManager


class ModelTextGenerator():
	def __init__(self):
		self.bot_configuration_manager: BotConfigurationManager = BotConfigurationManager()
		self.text_generation_parameters = {
			'max_length': 1024,
			'num_return_sequences': 1,
			'temperature': 0.8,
			'top_k': 40,
			'repetition_penalty': 1.008,
			'do_sample': True,
			'stop_token': '<|endoftext|>'
		}

	def generate_text_with_no_wrapper(self, bot_username: str, prompt_text: str, device_id: str):
		model = None
		encoded_prompt = None
		try:
			bot_config = self.bot_configuration_manager.get_configuration_by_name(bot_username)

			tokenizer = GPT2Tokenizer.from_pretrained(bot_config.Model)

			encoded_prompt = tokenizer.encode(prompt_text, add_special_tokens=False, return_tensors="pt")

			if len(encoded_prompt.data[0]) > self.text_generation_parameters['max_length']:
				logging.info(
					f":: Size of Tensor {encoded_prompt.data[0]} > {self.text_generation_parameters['max_length']}. Rejecting Attempt to Process Input")
				return None

			model = LanguageGenerationModel("gpt2", bot_config.Model, use_cuda=True, cuda_device=device_id, args={'fp16': False})

			start_time = time.time()

			output_list = model.generate(prompt=prompt_text, args=self.text_generation_parameters)

			result = output_list[0]

			logging.info(f":: Result {result.replace(prompt_text, '')}")

			if len(result) == len(prompt_text):
				logging.info(f"Prompt and Result Are Identical")
				return None

			end_time = time.time()
			duration = round(end_time - start_time, 1)

			logging.debug(f'{len(output_list)} sample(s) of text generated in {duration} seconds.')

			if output_list:
				return output_list[0]

			# encoded_prompt = encoded_prompt.to(device)
			#
			# model = GPT2LMHeadModel.from_pretrained(bot_config.Model)
			#
			# model = model.to(device)
			#
			# output_sequences = model.generate(
			# 	input_ids=encoded_prompt,
			# 	max_length=self.text_generation_parameters['max_length'],
			# 	top_k=self.text_generation_parameters['top_k'],
			# 	temperature=self.text_generation_parameters['temperature'],
			# 	repetition_penalty=self.text_generation_parameters['repetition_penalty'],
			# 	num_return_sequences=self.text_generation_parameters['num_return_sequences']
			# )
			#
			# text_generations = []
			#
			# for i in range(self.text_generation_parameters['num_return_sequences']):
			# 	decoded_text = tokenizer.decode(output_sequences[i], skip_special_tokens=False)
			# 	text_generations.append(decoded_text)
			# 	output = tokenizer.decode(output_sequences[i], skip_special_tokens=False)
			# 	foo = output.replace(prompt_text, "").replace("<|endoftext|>", "")
			# 	logging.info(f"Generated {i}: " + "\n" f"Prompt\n{prompt_text}\nResult\n{foo}\n{15 * '='}")

			# end_time = time.time()
			# duration = round(end_time - start_time, 1)
			#
			# if len(text_generations) == 0:
			# 	assert Exception("No text generated throwing for re-try")
			#
			# logging.info(f'{len(text_generations)} sample(s) of text generated in {duration} seconds.')
			#
			# returned_generation = text_generations[0]
			# if not self.text_is_valid(returned_generation, prompt_text):
			# 	assert Exception("Text not valid throw for re-try")
			#
			# return returned_generation

		except Exception as e:
			logging.error(f":: An error has occurred while attempting to generate text")
			logging.error(e)
		finally:
			pass
			# torch.cuda.empty_cache()

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

	def text_is_valid(self, generated_text, prompt):
		new_text = generated_text[len(prompt):]
		if '<|' not in new_text:
			logging.info("Validation failed, no end tag")
			return False
		return True
