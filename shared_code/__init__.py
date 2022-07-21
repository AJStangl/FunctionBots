import logging
NEW_LOG_FORMAT = '%(asctime)s (%(threadName)s) %(levelname)s %(message)s'
logging.basicConfig(format=NEW_LOG_FORMAT, level=logging.INFO)