import os
from sqlalchemy import create_engine
import psycopg2
conn_string = "host='localhost' dbname='redditData' user='postgres' password='guitar!01'"
conn = psycopg2.connect(conn_string)

user = os.environ['PsqlUser']
password = os.environ['PsqlPassword']
engine = create_engine(f"postgresql://{user}:{password}@localhost:5432/redditData", pool_size=10, max_overflow=-1)



