from pymongo import MongoClient
from config import configure

# database dependencies
uri = configure.get('DATABASE_AUTH')
client = MongoClient(uri)


###########################################
## Defining the databases and collections ##
###########################################

PlayersDB = client.PlayersDB
players = PlayersDB["players"]
