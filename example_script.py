from azure.data.tables import TableClient
from praw import Reddit
from praw.models import Subreddit

from shared_code.helpers.reddit_helper import RedditHelper
from shared_code.models.bot_configuration import BotConfigurationManager, BotConfiguration
from shared_code.storage_proxies.table_proxy import TableServiceProxy, TableRecord


def run():
	proxy: TableServiceProxy = TableServiceProxy()
	client: TableClient = proxy.get_client()
	query_string = ""
	client.query_entities()



if __name__ == '__main__':
	run()
