class InputTableRecord:
	id: str
	name_id: str
	subreddit: str
	input_type: str
	content_date_submitted_utc: int
	author: str
	responding_bot: str
	text_generation_prompt: str
	text_generation_response: str
	has_responded: bool

	def __init__(self, id: str, name_id: str, subreddit: str, input_type: str, content_date_submitted_utc: int,
				 author: str, responding_bot: str, text_generation_prompt: str, text_generation_response: str,
				 has_responded: bool):
		self.id = id
		self.name_id = name_id
		self.subreddit = subreddit
		self.input_type = input_type
		self.content_date_submitted_utc = content_date_submitted_utc
		self.author = author
		self.responding_bot = responding_bot
		self.text_generation_prompt = text_generation_prompt
		self.text_generation_response = text_generation_response
		self.has_responded = has_responded

	def to_dictionary(self) -> dict:
		record_dict = {
			'source_name': self.source_name,
			'created_utc': self.created_utc,
			'author': self.author,
			'subreddit': self.subreddit,
			'bot_username': self.bot_username,
			'input_type': self.input_type
		}
		return record_dict

	def to_json(self) -> str:
		import json
		return json.dumps(self.to_dictionary())