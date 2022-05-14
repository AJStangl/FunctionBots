class PrawQueueMessage(object):
	input_type: str
	source_name: str
	created_utc: str
	author: str
	subreddit: str
	bot_username: str

	def __init__(self, source_name: str, created_utc: str, author: str, subreddit: str, bot_username: str,
				 input_type: str) -> object:
		self.source_name = source_name
		self.created_utc = created_utc
		self.author = author
		self.subreddit = subreddit
		self.bot_username = bot_username
		self.input_type = input_type

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

	@staticmethod
	def from_json(data: dict[str]):
		return PrawQueueMessage(
			input_type=data["input_type"],
			source_name=data["source_name"],
			created_utc=data["created_utc"],
			author=data["author"],
			subreddit=data["subreddit"],
			bot_username=data["bot_username"])

	def get_partition_key(self) -> str:
		return f"{self.subreddit}|{self.bot_username}"
