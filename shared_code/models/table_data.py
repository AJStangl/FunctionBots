from dataclasses import dataclass, asdict
import json
from enum import Enum


@dataclass
class TableRecord:
	PartitionKey: str
	RowKey: str
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
	status: int
	time_in_hours: float


	@property
	def __dict__(self):
		"""
		get a python dictionary
		"""
		return asdict(self)

	@property
	def json(self):
		"""
		get the json formated string
		"""
		return json.dumps(self.__dict__)

	@classmethod
	def from_json(cls, json_key, json_string: dict):
		return cls(**json_string[json_key])


class Status(Enum):
	PENDING = 0
	INFLIGHT = 1
	SKIPPED = 2
	FAILED = 3
	COMPLETED = 4
