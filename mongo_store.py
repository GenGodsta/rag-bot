from langgraph.store.base import BaseStore, Item, SearchItem
from motor.motor_asyncio import AsyncIOMotorCollection
from datetime import datetime
from typing import Any, Optional
import json


class MongoStore(BaseStore):
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    def _ns_key(self, namespace: tuple) -> str:
        return ".".join(namespace)

    async def aput(self, namespace: tuple, key: str, value: dict) -> None:
        searchable = value.get("content") or json.dumps(value)  # adjust to your actual fact schema
        await self.collection.update_one(
            {"namespace": self._ns_key(namespace), "key": key},
            {"$set": {
                "namespace": self._ns_key(namespace),
                "key": key,
                "value": value,
                "search_text": searchable,
                "updated_at": datetime.utcnow()
            }},
            upsert=True
        )

    async def aget(self, namespace: tuple, key: str) -> Optional[Item]:
        doc = await self.collection.find_one({"namespace": self._ns_key(namespace), "key": key})
        if not doc:
            return None
        return Item(
            namespace=namespace, key=key, value=doc["value"],
            created_at=doc.get("updated_at"), updated_at=doc.get("updated_at")
        )

    async def asearch(self, namespace: tuple, query: str = None, limit: int = 20) -> list[SearchItem]:
        filter_ = {"namespace": self._ns_key(namespace)}
        if query:
            filter_["$text"] = {"$search": query}
        cursor = self.collection.find(filter_).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [
            SearchItem(namespace=namespace, key=d["key"], value=d["value"],
                    created_at=d.get("updated_at"), updated_at=d.get("updated_at"), score=None)
            for d in docs
        ]

    async def adelete(self, namespace: tuple, key: str) -> None:
        await self.collection.delete_one({"namespace": self._ns_key(namespace), "key": key})

    def put(self, *a, **kw): raise NotImplementedError("Use aput")
    def get(self, *a, **kw): raise NotImplementedError("Use aget")
    def search(self, *a, **kw): raise NotImplementedError("Use asearch")
    def delete(self, *a, **kw): raise NotImplementedError("Use adelete")
    def batch(self, *a, **kw): raise NotImplementedError
    async def abatch(self, *a, **kw): raise NotImplementedError