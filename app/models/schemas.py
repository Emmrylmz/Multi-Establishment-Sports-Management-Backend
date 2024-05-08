from pydantic import BaseModel, EmailStr, validator, constr, Field
from typing import List, Optional, Literal
from datetime import datetime


class ContactInfo(BaseModel):
    phone: Optional[str] = None


class ContactPerson(ContactInfo):
    name: Optional[str] = None
    email: Optional[EmailStr] = None


class PersonalAttributesBase(BaseModel):
    age: Optional[int] = None


class CreateUserSchema(BaseModel):
    email: EmailStr
    password: constr(min_length=8)
    passwordConfirm: str
    name: str
    photo: Optional[str] = (None,)
    role: Literal["Coach", "Player", "Manager"] = "Player"
    contact_info: Optional[ContactInfo] = None
    family_contacts: Optional[List[ContactPerson]] = []
    teams: List[str] = []
    personal_attributes: Optional[PersonalAttributesBase] = None
    created_at: datetime = None

    @validator("email", pre=True, always=True)
    def normalize_email(cls, v):
        if v is not None:
            return v.lower()
        return v  # Return None or a default value if email is not provided

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "strongpassword",
                "name": "John Doe",
            }
        }


# THIS PART FOR RESPONSES


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
