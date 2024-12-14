from pymongo import AsyncMongoClient
import os
import dotenv
import logging

dotenv.load_dotenv()

mongoURI = os.getenv('MONGO_URI')

mongo = AsyncMongoClient(mongoURI)

async def check_status():
    try:
        status = await mongo.admin.command('ping')
        if status['ok'] == 1:
            logging.info('Mongo OK')
        else:
            logging.error('Error connecting to MongoDB')
            raise Exception('Couldnt connect to mongodb')
    except Exception as e:
        logging.error(f'Error connecting to MongoDB: {e}')
        raise e
    
class Mongo:
    def __init__(self, db):
        self.db = mongo[db]

    async def insert_one(self, collection, data):
       try:
           print(f"attempting to inssert: {data}")
           await self.db[collection].insert_one(data)
       except Exception as e:
           logging.error(f'Error inserting data into MongoDB: {e}')
           raise e
       
    async def find_one(self, collection, query):
        try:
            return await self.db[collection].find_one(query)
        except Exception as e:
            logging.error(f'Error finding data in MongoDB: {e}')
            raise e
        
    async def find(self, collection, query):
        try:
            cursor = self.db[collection].find(query)
            results = []
            async for document in cursor:
                results.append(document)
            print(f"Found {len(results)} documents")  # Debug print
            return results
        except Exception as e:
            logging.error(f'Error finding data in MongoDB: {e}')
            raise e
        
    async def update_one(self, collection, query, data):
        try:
            update = {'$set': data}
            await self.db[collection].update_one(query, update)
        except Exception as e:
            logging.error(f'Error updating data in MongoDB: {e}')
            raise e

    async def delete_one(self, collection, query):
        try:
            await self.db[collection].delete_one(query)
        except Exception as e:
            logging.error(f'Error deleting data in MongoDB: {e}')
            raise e
        
    async def delete_many(self, collection, query):
        try:
            await self.db[collection].delete_many(query)
        except Exception as e:
            logging.error(f'Error deleting data in MongoDB: {e}')
            raise e