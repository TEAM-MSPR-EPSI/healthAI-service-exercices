import os
from motor.motor_asyncio import AsyncIOMotorClient

client = None
db = None

async def connect():
    global client, db
    client = AsyncIOMotorClient(os.getenv("MONGODB_URL"))
    db = client[os.getenv("MONGODB_DB")]

async def disconnect():
    if client:
        client.close()

def get_db():
    return db