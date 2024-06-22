from pydantic import BaseModel, EmailStr, validator, constr, Field
from typing import List, Optional, Literal
from datetime import datetime
from bson.objectid import ObjectId as BsonObjectId


class PydanticObjectId(BsonObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, BsonObjectId):
            raise TypeError("ObjectId required")
        return str(v)


class CreateUserSchema(BaseModel):
    email: EmailStr
    password: constr(min_length=8)
    passwordConfirm: str
    name: str
    role: Literal["Coach", "Player", "Manager"] = "Player"
    teams: List[str] = []

    @validator("email", pre=True, always=True)
    def normalize_email(cls, v):
        if v is not None:
            return v.lower()
        return v  # Return None or a default value if email is not provided

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "passwordConfirm": "strongpassword",
                "password": "strongpassword",
                "name": "John Doe",
                "team_ids": ["team_bson_object_id"],
            }
        }


class User(BaseModel):
    _id: str
    name: str
    role: Literal["Coach", "Player", "Manager"]
    email: str
    teams: List[PydanticObjectId] = []

    class Config:
        orm_mode = True
        fields = {"id": "_id"}


class UserResponseSchema(BaseModel):
    status: str
    access_token: str
    user: dict

    class Config:
        orm_mode = True
        fields = {"id": "_id"}


class ContactInfo(BaseModel):
    phone: Optional[str] = None


class ContactPerson(ContactInfo):
    name: Optional[str] = None
    email: Optional[EmailStr] = None


# THIS PART FOR RESPONSES


class UserAttributesSchema(BaseModel):
    age: int
    height: float
    weight: float
    photo: str = None
    contact_info: List[ContactInfo] = None
    family_contacts: Optional[List[ContactPerson]] = []
    on_boarding = bool = True
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        json_encoders = {datetime: lambda o: o.isoformat()}


class LoginUserSchema(BaseModel):
    email: EmailStr
    password: constr(min_length=8)


class UserResponse(BaseModel):
    status: str
    user: UserResponseSchema
