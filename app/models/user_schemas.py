from pydantic import BaseModel, EmailStr, validator, constr, Field
from typing import List, Optional, Literal
from datetime import datetime


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


class UserResponseSchema(BaseModel):
    name: Optional[str]
    email: Optional[EmailStr]  # Make email optional if it could be None
    photo: Optional[str]
    role: Optional[str]
    # Remove sensitive data fields from the response model
    created_at: Optional[datetime]


class UserResponse(BaseModel):
    status: str
    user: UserResponseSchema
