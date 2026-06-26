from pydantic import BaseModel,Field
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls,v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectID")
        return ObjectId(v)
    

class RAGDB(BaseModel):
    chunkid:PyObjectId=Field(default_factory=PyObjectId, alias="_id")
    chunk:str
    source:str
    page:int

    class Config:
        json_encoders={ObjectId:str}
        populate_by_name=True

class chatrequest(BaseModel):
    query: str
    topk:int=5

class chatresponse(BaseModel):
    answer:str
    sources:list
