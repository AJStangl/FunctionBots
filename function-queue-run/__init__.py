import logging

import azure.functions as func

from shared_code.services.main_run_service import BotMonitorService


async def main(message: func.QueueMessage) -> None:
	logging.info(f":: Starting BotMonitorService")
	bot_run_service: BotMonitorService = BotMonitorService()
	return await bot_run_service.invoke(message)
# 	all_workers = ["worker-1", "worker-2", "worker-3"]
#
# 	reddit_helper: RedditManager = RedditManager()
#
# 	repository: DataRepository = DataRepository()
#
# 	queue_proxy: QueueServiceProxy = QueueServiceProxy()
#
# 	message_json = message.get_body().decode('utf-8')
#
# 	incoming_message: BotConfiguration = json.loads(message_json, object_hook=lambda d: BotConfiguration(**d))
#
# 	bot_name = incoming_message.Name
#
# 	logging.info(f":: Starting Main Routine For {bot_name}")
#
# 	reddit: Reddit = reddit_helper.get_praw_instance_for_bot(bot_name)
#
# 	tagging_mixin: TaggingMixin = TaggingMixin(reddit)
#
# 	reply_service: ReplyService = ReplyService()
#
# 	reply_logic: ReplyLogic = ReplyLogic(reddit)
#
# 	user = reddit.user.me()
#
# 	subs = reddit_helper.get_subs_from_configuration(bot_name)
#
# 	subreddit: Subreddit = await reddit.subreddit(subs)
#
# 	logging.info(f":: Initializing Reply Before Main Routine for {bot_name}")
#
# 	await reply_service.invoke()
#
# 	####################################################################################################################
# 	logging.info(f":: Handling pending comments and submissions from database for {bot_name}")
#
# 	logging.info(f":: Fetching latest Comments For {bot_name}")
# 	pending_comments = repository.search_for_pending("Comment", bot_name, 22)
#
# 	logging.info(f":: Fetching latest Submissions For {bot_name}")
# 	pending_submissions = repository.search_for_pending("Submission", bot_name, 10)
#
# 	for record in chain_listing_generators(pending_comments, pending_submissions):
# 		if record is None:
# 			logging.info(f":: No records found for comments or submission to process for {bot_name}")
# 			continue
#
# 		# Extract the record and set the status
# 		record = record['TableRecord']
# 		record.Status = 1
# 		processed = await process_input(record, reddit, tagging_mixin)
# 		if processed is None:
# 			logging.info(f":: Failed To Process {record.RedditId} for {record.RespondingBot}")
# 			continue
#
# 		record.TextGenerationPrompt = processed
#
# 		# 8 hours to live before removing message from queue
# 		message_live_in_hours = 60 * 60 * 8
#
# 		# randomly select between 1 and 50
# 		reply_probability_target = random.randint(0, 50)
#
# 		if record.InputType == "Submission":
# 			repository.update_entity(record)
# 			queue = queue_proxy.service.get_queue_client(random.choice(all_workers), message_encode_policy=TextBase64EncodePolicy())
# 			queue.send_message(json.dumps(record.as_dict()), time_to_live=message_live_in_hours)
# 			logging.info(f":: Sending {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation")
# 			continue
#
# 		if record.ReplyProbability > reply_probability_target and record.InputType == "Comment":
# 			queue = queue_proxy.service.get_queue_client(random.choice(all_workers), message_encode_policy=TextBase64EncodePolicy())
# 			queue.send_message(json.dumps(record.as_dict()), time_to_live=message_live_in_hours)
# 			repository.update_entity(record)
# 			logging.info(f":: Sending {record.InputType} for {record.RespondingBot} to Queue For Model Text Generation")
# 			continue
#
# 		else:
# 			logging.info(
# 				f":: Ignoring {record.InputType} for {record.RespondingBot} has a Probability of {record.ReplyProbability} but needs {reply_probability_target}")
# 			record.Status = 2
# 			repository.update_entity(record)
# 			continue
#
# 	####################################################################################################################
# 	max_search_time = int(os.environ["MaxSearchSeconds"])
#
# 	logging.info(f":: Collecting Submissions for {bot_name}")
# 	start_time: float = time.time()
# 	async for submissions in subreddit.stream.submissions(pause_after=0, skip_existing=False):
# 		if submissions is None:
# 			continue
#
# 		if round(time.time() - start_time) > max_search_time:
# 			logging.info(f":: Halting Collection Past {max_search_time} seconds For Submissions")
# 			break
# 		insert_submission_to_table(submissions, user, repository, reply_logic)
#
# 	start_time = time.time()
# 	logging.info(f":: Collecting Comments for {bot_name}")
# 	async for comment in subreddit.comments(pause_after=0, skip_existing=False):
# 		if comment is None:
# 			continue
#
# 		if round(time.time() - start_time) > max_search_time:
# 			logging.info(f":: Halting Collection Past {max_search_time} seconds For Comments")
# 			break
# 		await insert_comment_to_table(comment, user, repository, reply_logic, reddit)
# 	####################################################################################################################
#
# 	logging.info(f":: Initializing Reply After Main Routine for {bot_name}")
# 	await reply_service.invoke()
#
# 	logging.info(f":: Polling Method Complete For {bot_name}")
# 	return None
#
#
# async def process_input(record: TableRecord, instance: Reddit, tagging_mixin: TaggingMixin) -> Optional[str]:
# 	if record.InputType == "Submission":
# 		thing: Submission = await instance.submission(id=record.RedditId)
# 		history: str = await tagging_mixin.collate_tagged_comment_history(thing)
# 		cleaned_history: str = tagging_mixin.remove_username_mentions_from_string(history, record.RespondingBot)
# 		reply_start_tag = await tagging_mixin.get_reply_tag(thing, record.RespondingBot)
# 		prompt = cleaned_history + reply_start_tag
# 		return prompt
#
# 	if record.InputType == "Comment":
# 		thing = await instance.comment(id=record.RedditId)
# 		if thing is None:
# 			return None
# 		history = await tagging_mixin.collate_tagged_comment_history(thing)
# 		cleaned_history = tagging_mixin.remove_username_mentions_from_string(history, record.RespondingBot)
# 		reply_start_tag = await tagging_mixin.get_reply_tag(thing, record.RespondingBot)
# 		prompt = cleaned_history + reply_start_tag
# 		return prompt
#
#
# def insert_submission_to_table(submission: Submission, user: Redditor, repository: DataRepository, reply_probability: ReplyLogic) -> Optional[TableRecord]:
# 	# Ignore when submission is the same for the submitter and responder
# 	if user.name == getattr(submission.author, 'name', ''):
# 		return None
#
# 	probability = reply_probability.calculate_reply_probability(submission)
#
# 	if probability == 0:
# 		logging.debug(f":: Reply Probability for {submission.id} is {probability} for bot - {user.name}")
# 		return None
#
# 	mapped_input: TableRecord = TableHelper.map_base_to_message(
# 		reddit_id=submission.id,
# 		sub_reddit=submission.subreddit.display_name,
# 		input_type="Submission",
# 		time_in_hours=timestamp_to_hours(submission.created),
# 		submitted_date=submission.created,
# 		author=getattr(submission.author, 'name', ''),
# 		responding_bot=user.name,
# 		reply_probability=probability,
# 		url=submission.url
# 	)
#
# 	logging.info(f":: Inserting Record submission {submission.id} with probability {probability} for {user.name}")
# 	entity = repository.create_if_not_exist(mapped_input)
#
# 	return entity
#
#
# async def insert_comment_to_table(comment: Comment, user: Redditor, repository: DataRepository, reply_probability: ReplyLogic, instance: Reddit) -> Optional[TableRecord]:
# 	probability = reply_probability.calculate_reply_probability(comment)
# 	submission = await instance.submission(id=comment.submission.id)
# 	if probability == 0:
# 		logging.debug(f":: Reply Probability for {comment.id} is {probability} for bot - {user.name}")
# 		return None
#
# 	mapped_input: TableRecord = TableHelper.map_base_to_message(
# 		reddit_id=comment.id,
# 		sub_reddit=comment.subreddit.display_name,
# 		input_type="Comment",
# 		submitted_date=submission.created,
# 		author=getattr(comment.author, 'name', ''),
# 		responding_bot=user.name,
# 		time_in_hours=timestamp_to_hours(comment.created),
# 		reply_probability=probability,
# 		url=comment.permalink)
#
# 	logging.info(f":: Inserting Record comment {comment.id} with probability {probability} for {user.name}")
# 	entity = repository.create_if_not_exist(mapped_input)
#
# 	return entity
#
#
# def timestamp_to_hours(utc_timestamp):
# 	return int((datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(utc_timestamp)).total_seconds() / 3600) - 4
#
#
# def chain_listing_generators(*iterables):
# 	# Special tool for chaining PRAW's listing generators
# 	# It joins the three iterables together so that we can DRY
# 	for it in iterables:
# 		for element in it:
# 			if element is None:
# 				break
# 			else:
# 				yield element
