class PrawQueueMessage:
	source_name: str
	created_utc: str
	author: str
	subreddit: str
	bot_username: str

	def __init__(self, source_name: str, created_utc: str, author: str , subreddit: str, bot_username: str):
		self.source_name = source_name
		self.created_utc = created_utc
		self.author = author
		self.subreddit = subreddit
		self.bot_username = bot_username

	def to_dictionary(self) -> dict:
		record_dict = {
			'source_name': self.source_name,
			'created_utc': self.created_utc,
			'author': self.author,
			'subreddit': self.subreddit,
			'bot_username': self.bot_username
		}
		return record_dict

	def to_json(self) -> str:
		import json
		return json.dumps(self.to_dictionary())
