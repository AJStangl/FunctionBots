from dataclasses import dataclass
from dataclasses_serialization.json import JSONSerializer

@dataclass
class PrawQueueMessage:
	source_name: str
	created_utc: str
	author: str
	subreddit: str
	bot_username: str
