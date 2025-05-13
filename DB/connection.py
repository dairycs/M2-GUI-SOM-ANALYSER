# connection.py

from pymongo import MongoClient

class MongoDBManager:
    def __init__(self, uri, db_name):
        self.uri = uri
        self.db_name = db_name
        self.client = None
        self.db = None

    def connect(self):
        try:
            self.client = MongoClient(self.uri)
            self.db = self.client[self.db_name]
            print(f"✅ Connected to MongoDB at {self.uri}, database: {self.db_name}")
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            self.client = None
            self.db = None

    def get_collections(self):
        if self.db is not None:
            return self.db.list_collection_names()
        return []

    def get_documents(self, collection_name, query=None, limit=None):
        if self.db is not None:
            collection = self.db[collection_name]
            cursor = collection.find(query or {})
            if limit is not None:
                cursor = cursor.limit(int(limit))  # 💡 only apply if limit is set
            return list(cursor)
        return []

