class InputTableRecord:
	partition_key: str
	row_key: str
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

	def __init__(self):
		return

	def to_dictionary(self) -> dict:
		record_dict = {
			'PartitionKey': self.partition_key,
			'RowKey': self.row_key,
			'id': self.id,
			'name_id': self.name_id,
			'subreddit': self.subreddit,
			'input_type': self.input_type,
			'content_date_submitted_utc': self.content_date_submitted_utc,
			'author': self.author,
			'responding_bot': self.responding_bot,
			'text_generation_prompt': self.text_generation_prompt,
			'text_generation_response': self.text_generation_response,
			'has_responded': self.has_responded
		}
		return record_dict

	def to_json(self) -> str:
		import json
		return json.dumps(self.to_dictionary())
