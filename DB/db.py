from pymongo import MongoClient
from typing import List, Dict

class MongoDBClient:
    def __init__(self, uri: str, db_name: str):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]

    def list_collections(self) -> List[str]:
        return self.db.list_collection_names()

    def get_documents(self, collection_name: str, query: Dict = {}, limit: int = 1000) -> List[Dict]:
        collection = self.db[collection_name]
        return list(collection.find(query).limit(limit))

    def get_sample_document(self, collection_name: str) -> Dict:
        collection = self.db[collection_name]
        return collection.find_one()
