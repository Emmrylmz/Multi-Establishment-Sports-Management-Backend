# from pydantic import BaseModel, Field
# from typing import Optional
# from datetime import datetime
# from bson import ObjectId
# from enum import Enum


# class PyObjectId(ObjectId):
#     @classmethod
#     def __get_validators__(cls):
#         yield cls.validate

#     @classmethod
#     def validate(cls, v):
#         if not ObjectId.is_valid(v):
#             raise ValueError("Invalid objectid")
#         return ObjectId(v)

#     @classmethod
#     def __modify_schema__(cls, field_schema):
#         field_schema.update(type="string")


# class RequestStatus(str, Enum):
#     pending = "pending"
#     approved = "approved"
#     rejected = "rejected"


# class PrivateLessonRequestBase(BaseModel):
#     coach_id: PyObjectId = Field(...)
#     preferred_date: datetime = Field(...)
#     preferred_time: str = Field(...)
#     notes: str = Field(...)


# class PrivateLessonRequestCreate(PrivateLessonRequestBase):
#     pass


# class PrivateLessonRequestUpdate(BaseModel):
#     status: RequestStatus
#     response_notes: Optional[str] = None


# class PrivateLessonRequestInDB(PrivateLessonRequestBase):
#     id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
#     player_id: PyObjectId = Field(...)
#     status: RequestStatus = Field(default=RequestStatus.pending)
#     request_date: datetime = Field(default_factory=datetime.utcnow)
#     response_date: Optional[datetime] = None
#     response_notes: Optional[str] = None

#     class Config:
#         allow_population_by_field_name = True
#         arbitrary_types_allowed = True
#         json_encoders = {ObjectId: str}


# class PrivateLessonRequestOut(PrivateLessonRequestInDB):
#     pass
