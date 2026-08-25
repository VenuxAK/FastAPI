from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import fastapi_blog.models
from fastapi_blog.database import get_db
from fastapi_blog.schemas import PostResponse, UserCreate, UserResponse, UserUpdate

router = APIRouter()

router.prefix = "/users"


# Get user by id
@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        Select(fastapi_blog.models.User).where(fastapi_blog.models.User.id == user_id)
    )
    user = result.scalars().first()

    if user:
        return user

    raise HTTPException(status_code=404, detail="User not found")


# Create new user
@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):

    # Validate username
    result = await db.execute(
        Select(fastapi_blog.models.User).where(
            fastapi_blog.models.User.username == user.username
        )
    )
    existing_username = result.scalars().first()
    if existing_username:
        raise HTTPException(status_code=422, detail="Username already taken.")

    # Validate email
    result = await db.execute(
        Select(fastapi_blog.models.User).where(
            fastapi_blog.models.User.email == user.email
        )
    )
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(status_code=422, detail="Email already taken.")

    new_user = fastapi_blog.models.User(username=user.username, email=user.email)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


# Get user's posts
@router.get(
    "/{user_id}/posts",
    response_model=list[PostResponse],
    status_code=status.HTTP_200_OK,
)
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):

    result = await db.execute(
        Select(fastapi_blog.models.User).where(fastapi_blog.models.User.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        Select(fastapi_blog.models.Post)
        .where(fastapi_blog.models.Post.user_id == user.id)
        .options(selectinload(fastapi_blog.models.Post.author))
    )

    posts = result.scalars().all()

    return posts


# Get user's post by post id
@router.get("/{user_id}/posts/{post_id}", response_model=PostResponse, status_code=200)
async def get_user_post(
    user_id: int, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        Select(fastapi_blog.models.User).where(fastapi_blog.models.User.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        Select(fastapi_blog.models.Post).where(fastapi_blog.models.Post.id == post_id)
    )
    post = result.scalars().first()
    if not post:
        raise HTTPException(404, detail="Post not found")

    result = await db.execute(
        Select(fastapi_blog.models.Post)
        .where(
            fastapi_blog.models.Post.id == post_id
            and fastapi_blog.models.Post.user_id == user_id
        )
        .options(selectinload(fastapi_blog.models.Post.author))
    )

    post = result.scalars().first()

    return post


# Update user profile
@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def update_user_profile(
    user_id: int, data: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        Select(fastapi_blog.models.User).where(fastapi_blog.models.User.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if data.email is not None and user.email != data.email:
        result = await db.execute(
            Select(fastapi_blog.models.User).where(
                fastapi_blog.models.User.email == data.email
            )
        )
        existing_user = result.scalars().first()

        if existing_user:
            raise HTTPException(status_code=400)

    if data.username is not None and user.username != data.username:
        result = await db.execute(
            Select(fastapi_blog.models.User).where(
                fastapi_blog.models.User.username == data.username
            )
        )
        existing_user = result.scalars().first()

        if existing_user:
            raise HTTPException(status_code=400)

    if data.email is not None:
        user.email = data.email
    if data.username is not None:
        user.username = data.username
    if data.image_file is not None:
        user.image_file = data.image_file

    await db.commit()
    await db.refresh(user)
    return user


# Delete user profile
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_profile(
    user_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        Select(fastapi_blog.models.User).where(fastapi_blog.models.User.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(404, "User not found")

    if user.posts:
        raise HTTPException(400, "User cannot be deleted")

    await db.delete(user)
    await db.commit()
