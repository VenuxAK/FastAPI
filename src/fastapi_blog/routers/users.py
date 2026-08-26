from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import Select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fastapi_blog.auth import (
    create_access_token,
    hash_password,
    oauth2_scheme,
    verify_access_token,
    verify_password,
)
from fastapi_blog.config import settings
from fastapi_blog.database import get_db
from fastapi_blog.models import Post, User
from fastapi_blog.schemas import (
    PostResponse,
    Token,
    UserCreate,
    UserPrivate,
    UserPublic,
    UserUpdate,
)

router = APIRouter()

router.prefix = "/users"


# Get user profile
@router.get("/me", response_model=UserPrivate)
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get the currently authenticated user."""
    user_id = verify_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate user_id is a valid integer (defense against malformed JWT)
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(
        Select(User).where(User.id == user_id_int),
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# Get user by id
@router.get("/{user_id}", response_model=UserPublic, status_code=status.HTTP_200_OK)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(Select(User).where(User.id == user_id))
    user = result.scalars().first()

    if user:
        return user

    raise HTTPException(status_code=404, detail="User not found")


# Create new user
@router.post("", response_model=UserPrivate, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):

    # Validate username
    result = await db.execute(Select(User).where(User.username == user.username))
    existing_username = result.scalars().first()
    if existing_username:
        raise HTTPException(status_code=422, detail="Username already taken.")

    # Validate email
    result = await db.execute(Select(User).where(User.email == user.email))
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(status_code=422, detail="Email already taken.")

    new_user = User(
        username=user.username, email=user.email, password=hash_password(user.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Look up user by email (case-insensitive)
    # Note: OAuth2PasswordRequestForm uses "username" field, but we treat it as email
    result = await db.execute(
        Select(User).where(
            func.lower(User.email) == form_data.username.lower(),
        ),
    )
    user = result.scalars().first()

    # Verify user exists and password is correct
    # Don't reveal which one failed (security best practice)
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token with user id as subject
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


# Get user's posts
@router.get(
    "/{user_id}/posts",
    response_model=list[PostResponse],
    status_code=status.HTTP_200_OK,
)
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):

    result = await db.execute(Select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        Select(Post).where(Post.user_id == user.id).options(selectinload(Post.author))
    )

    posts = result.scalars().all()

    return posts


# Get user's post by post id
@router.get("/{user_id}/posts/{post_id}", response_model=PostResponse, status_code=200)
async def get_user_post(
    user_id: int, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(Select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(Select(Post).where(Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(404, detail="Post not found")

    result = await db.execute(
        Select(Post)
        .where(Post.id == post_id and Post.user_id == user_id)
        .options(selectinload(Post.author))
    )

    post = result.scalars().first()

    return post


# Update user profile
@router.patch(
    "/{user_id}",
    response_model=UserPrivate,
    status_code=status.HTTP_201_CREATED,
)
async def update_user_profile(
    user_id: int, data: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(Select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if data.email is not None and user.email != data.email:
        result = await db.execute(Select(User).where(User.email == data.email))
        existing_user = result.scalars().first()

        if existing_user:
            raise HTTPException(status_code=400)

    if data.username is not None and user.username != data.username:
        result = await db.execute(Select(User).where(User.username == data.username))
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
    result = await db.execute(Select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(404, "User not found")

    if user.posts:
        raise HTTPException(400, "User cannot be deleted")

    await db.delete(user)
    await db.commit()
