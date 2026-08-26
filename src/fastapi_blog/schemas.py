from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=30)
    email: EmailStr = Field(max_length=100)


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=200)


class UserUpdate(UserBase):
    username: str | None = Field(default=None, min_length=1, max_length=30)
    email: EmailStr | None = Field(default=None, max_length=100)
    image_file: str | None = Field(default=None, min_length=1, max_length=200)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    image_file: str | None
    image_path: str


class UserPrivate(UserPublic):
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str


################ Post


class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)


class PostCreate(PostBase):
    user_id: int = 1  # TEMPORARY


class PostUpdate(PostBase):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    content: str | None = Field(default=None, min_length=1)
    user_id: int


class PostResponse(PostBase):

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    author: UserPublic
