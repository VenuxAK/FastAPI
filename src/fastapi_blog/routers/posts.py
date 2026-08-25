from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import fastapi_blog.models
from fastapi_blog.database import get_db
from fastapi_blog.schemas import PostCreate, PostResponse, PostUpdate

router = APIRouter()

router.prefix = "/posts"


# Get Posts
@router.get("", response_model=list[PostResponse], status_code=status.HTTP_200_OK)
async def get_all_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        Select(fastapi_blog.models.Post).options(
            selectinload(fastapi_blog.models.Post.author)
        )
    )
    posts = result.scalars().all()

    return posts


# Get Post by id
@router.get("/{post_id}", response_model=PostResponse, status_code=status.HTTP_200_OK)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):

    result = await db.execute(
        Select(fastapi_blog.models.Post)
        .where(fastapi_blog.models.Post.id == int(post_id))
        .options(selectinload(fastapi_blog.models.Post.author))
    )

    post = result.scalars().first()

    if not post:
        raise HTTPException(status_code=404, detail="Post Not Found")

    return post


# Create new post
@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):

    result = await db.execute(
        Select(fastapi_blog.models.User).where(
            fastapi_blog.models.User.id == post.user_id
        )
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(404, "User not found")

    new_post = fastapi_blog.models.Post(
        title=post.title, content=post.content, user_id=post.user_id
    )

    db.add(new_post)
    await db.commit()
    await db.refresh(new_post)
    return new_post


# Update post
@router.put(
    "/{post_id}",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def update_post(
    post_id: int, data: PostUpdate, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        Select(fastapi_blog.models.Post).where(fastapi_blog.models.Post.id == post_id)
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(404, "Post not found")

    if data.user_id != post.user_id:
        raise HTTPException(401, detail="Forbidden")

    post.title = data.title
    post.content = data.content

    await db.commit()
    await db.refresh(post)
    return post


# Update partial post data
@router.patch(
    "/{post_id}",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def update_partial_data_post(
    post_id: int, data: PostUpdate, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        Select(fastapi_blog.models.Post).where(fastapi_blog.models.Post.id == post_id)
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(404, "Post not found")

    if data.user_id != post.user_id:
        raise HTTPException(401, detail="Forbidden")

    updated_data = data.model_dump(exclude_unset=True)
    for key, value in updated_data.items():
        setattr(post, key, value)

    await db.commit()
    await db.refresh(post)
    return post


# Delete post
@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        Select(fastapi_blog.models.Post).where(fastapi_blog.models.Post.id == post_id)
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(404, "Post not found")

    await db.delete(post)
    await db.commit()
